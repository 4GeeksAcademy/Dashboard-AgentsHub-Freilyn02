try:
    # try to import flask, or return error if has not been installed
    from flask import Flask
    from flask import jsonify
    from flask import request
    from flask import send_from_directory
except ImportError:
    print("You don't have Flask installed, run `$ pip3 install flask` and try again")
    exit(1)

from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
import json
import os, subprocess, time
import smtplib
import socket
import ssl
import threading
import uuid
import urllib.error
import urllib.request

static_file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), './')
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 #disable cache


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

# Endpoint-specific rate limit settings for onboarding traffic.
ONBOARDING_LIMIT_PER_MINUTE = _env_int("ONBOARDING_LIMIT_PER_MINUTE", 120)
ONBOARDING_WINDOW_SECONDS = _env_int("ONBOARDING_WINDOW_SECONDS", 60)
onboarding_rate_limit_store = {}
onboarding_rate_limit_lock = threading.Lock()

# Payments webhook connector settings (Atlas).
PAYMENTS_WEBHOOK_TIMEOUT_SECONDS = _env_int("PAYMENTS_WEBHOOK_TIMEOUT_SECONDS", 15)
PAYMENTS_WEBHOOK_MAX_RETRIES = _env_int("PAYMENTS_WEBHOOK_MAX_RETRIES", 3)
PAYMENTS_WEBHOOK_BACKOFF_BASE_SECONDS = _env_int("PAYMENTS_WEBHOOK_BACKOFF_BASE_SECONDS", 1)
PAYMENTS_WEBHOOK_EXECUTOR_WORKERS = _env_int("PAYMENTS_WEBHOOK_EXECUTOR_WORKERS", 4)
payments_webhook_executor = ThreadPoolExecutor(max_workers=PAYMENTS_WEBHOOK_EXECUTOR_WORKERS)
payments_webhook_jobs = {}
payments_webhook_jobs_lock = threading.Lock()

# SMTP connector settings (Echo).
SMTP_RETRY_LIMIT = _env_int("SMTP_RETRY_LIMIT", 5)
SMTP_BACKOFF_BASE_SECONDS = _env_int("SMTP_BACKOFF_BASE_SECONDS", 1)
SMTP_EXECUTOR_WORKERS = _env_int("SMTP_EXECUTOR_WORKERS", 4)
smtp_executor = ThreadPoolExecutor(max_workers=SMTP_EXECUTOR_WORKERS)
smtp_jobs = {}
smtp_jobs_lock = threading.Lock()


def _get_client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _check_rate_limit(client_ip, now_ts):
    with onboarding_rate_limit_lock:
        bucket = onboarding_rate_limit_store.get(client_ip)
        if not bucket or now_ts >= bucket["reset_at"]:
            bucket = {
                "count": 0,
                "reset_at": now_ts + ONBOARDING_WINDOW_SECONDS,
            }

        bucket["count"] += 1
        onboarding_rate_limit_store[client_ip] = bucket

        retry_after = max(1, int(bucket["reset_at"] - now_ts))
        remaining = max(0, ONBOARDING_LIMIT_PER_MINUTE - bucket["count"])
        allowed = bucket["count"] <= ONBOARDING_LIMIT_PER_MINUTE
        return allowed, retry_after, remaining


def _post_json_with_timeout(url, payload):
    request_data = json.dumps(payload).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
    }
    outbound_request = urllib.request.Request(
        url=url,
        data=request_data,
        headers=request_headers,
        method="POST",
    )

    with urllib.request.urlopen(outbound_request, timeout=PAYMENTS_WEBHOOK_TIMEOUT_SECONDS) as response:
        response_body = response.read().decode("utf-8")
        return response.getcode(), response_body


def _run_payments_webhook_job(job_id, webhook_url, connector_payload):
    with payments_webhook_jobs_lock:
        payments_webhook_jobs[job_id]["status"] = "in_progress"
        payments_webhook_jobs[job_id]["started_at"] = int(time.time())

    last_error = ""
    for attempt in range(PAYMENTS_WEBHOOK_MAX_RETRIES + 1):
        try:
            status_code, response_body = _post_json_with_timeout(webhook_url, connector_payload)
            if 200 <= status_code < 300:
                with payments_webhook_jobs_lock:
                    payments_webhook_jobs[job_id]["status"] = "completed"
                    payments_webhook_jobs[job_id]["completed_at"] = int(time.time())
                    payments_webhook_jobs[job_id]["attempts"] = attempt + 1
                    payments_webhook_jobs[job_id]["response_status_code"] = status_code
                    payments_webhook_jobs[job_id]["response_body"] = response_body
                return

            last_error = f"Non-2xx response: {status_code}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as connector_error:
            last_error = str(connector_error)

        if attempt < PAYMENTS_WEBHOOK_MAX_RETRIES:
            backoff_seconds = PAYMENTS_WEBHOOK_BACKOFF_BASE_SECONDS * (2 ** attempt)
            time.sleep(backoff_seconds)

    with payments_webhook_jobs_lock:
        payments_webhook_jobs[job_id]["status"] = "warning"
        payments_webhook_jobs[job_id]["completed_at"] = int(time.time())
        payments_webhook_jobs[job_id]["attempts"] = PAYMENTS_WEBHOOK_MAX_RETRIES + 1
        payments_webhook_jobs[job_id]["warning"] = "Timeout in payments webhook connector"
        payments_webhook_jobs[job_id]["error"] = last_error

    print(f"[warning] Timeout in payments webhook connector for job {job_id}: {last_error}")


def _load_smtp_config():
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": smtp_port,
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASS", ""),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes", "on"),
        "use_ssl": os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes", "on"),
        "timeout_seconds": int(os.getenv("SMTP_TIMEOUT_SECONDS", "15")),
    }


def _parse_smtp_error(error):
    smtp_code = None
    smtp_message = str(error)

    if isinstance(error, smtplib.SMTPResponseException):
        smtp_code = int(error.smtp_code)
        if isinstance(error.smtp_error, bytes):
            smtp_message = error.smtp_error.decode("utf-8", errors="replace")
        else:
            smtp_message = str(error.smtp_error)

    return smtp_code, smtp_message


def _is_non_retryable_smtp_error(error, smtp_code):
    if isinstance(error, smtplib.SMTPAuthenticationError):
        return True
    if isinstance(error, smtplib.SMTPNotSupportedError):
        return True
    if smtp_code in (530, 534, 535, 550, 551, 553, 554):
        return True
    return False


def _smtp_connect(config):
    timeout_seconds = config["timeout_seconds"]
    if config["use_ssl"]:
        ssl_context = ssl.create_default_context()
        return smtplib.SMTP_SSL(config["host"], config["port"], timeout=timeout_seconds, context=ssl_context)
    return smtplib.SMTP(config["host"], config["port"], timeout=timeout_seconds)


def _smtp_login_if_needed(client, config):
    if config["use_tls"] and not config["use_ssl"]:
        ssl_context = ssl.create_default_context()
        client.starttls(context=ssl_context)

    if config["user"] and config["password"]:
        client.login(config["user"], config["password"])


def _send_smtp_message(config, from_email, to_email, subject, body_text):
    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body_text)

    with _smtp_connect(config) as smtp_client:
        smtp_client.ehlo()
        _smtp_login_if_needed(smtp_client, config)
        smtp_client.send_message(message)


def _run_smtp_job(job_id, email_payload):
    with smtp_jobs_lock:
        smtp_jobs[job_id]["status"] = "in_progress"
        smtp_jobs[job_id]["started_at"] = int(time.time())

    config = _load_smtp_config()
    non_retryable = False
    last_error_message = ""
    last_error_code = None

    for attempt in range(SMTP_RETRY_LIMIT + 1):
        try:
            _send_smtp_message(
                config,
                from_email=email_payload["from_email"],
                to_email=email_payload["to_email"],
                subject=email_payload["subject"],
                body_text=email_payload["body"],
            )

            with smtp_jobs_lock:
                smtp_jobs[job_id]["status"] = "completed"
                smtp_jobs[job_id]["completed_at"] = int(time.time())
                smtp_jobs[job_id]["attempts"] = attempt + 1
            return
        except (smtplib.SMTPException, socket.timeout, OSError, ValueError) as smtp_error:
            last_error_code, last_error_message = _parse_smtp_error(smtp_error)
            non_retryable = _is_non_retryable_smtp_error(smtp_error, last_error_code)

            print(
                f"[smtp][attempt {attempt + 1}] code={last_error_code} "
                f"non_retryable={non_retryable} error={last_error_message}"
            )

            if non_retryable:
                break

        if attempt < SMTP_RETRY_LIMIT:
            time.sleep(SMTP_BACKOFF_BASE_SECONDS * (2 ** attempt))

    with smtp_jobs_lock:
        smtp_jobs[job_id]["status"] = "warning"
        smtp_jobs[job_id]["completed_at"] = int(time.time())
        smtp_jobs[job_id]["attempts"] = attempt + 1
        smtp_jobs[job_id]["warning"] = "SMTP retry limit exceeded"
        smtp_jobs[job_id]["smtp_error"] = {
            "code": last_error_code,
            "message": last_error_message,
            "non_retryable": non_retryable,
        }

    print(
        f"[warning] SMTP retry limit exceeded for job {job_id}. "
        f"code={last_error_code} non_retryable={non_retryable} error={last_error_message}"
    )

# Serving the index file
@app.route('/', methods=['GET'])
def serve_dir_directory_index():
    if os.path.exists("app.py"):
        # if app.py exists we use the render function
        out = subprocess.Popen(['python3','app.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout,stderr = out.communicate()
        return stdout if out.returncode == 0 else f"<pre style='color: red;'>{stdout.decode('utf-8')}</pre>"
    if os.path.exists("index.html"):
        return send_from_directory(static_file_dir, 'index.html')
    else:
        return "<h1 align='center'>404</h1><h2 align='center'>Missing index.html file</h2><p align='center'><img src='https://github.com/4GeeksAcademy/html-hello/blob/main/.vscode/rigo-baby.jpeg?raw=true' /></p>"


@app.route('/api/onboarding/register', methods=['POST'])
def onboarding_register():
    now_ts = time.time()
    client_ip = _get_client_ip()
    allowed, retry_after, remaining = _check_rate_limit(client_ip, now_ts)

    if not allowed:
        response = jsonify({
            "status": 429,
            "error": "Too Many Requests",
            "message": "Rate limit reached in onboarding endpoint. Please retry after the provided delay.",
            "retry_after_seconds": retry_after
        })
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        response.headers["X-RateLimit-Limit"] = str(ONBOARDING_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = "0"
        return response

    payload = request.get_json(silent=True) or {}
    email = payload.get("email")

    response = jsonify({
        "status": "ok",
        "message": "Onboarding request accepted.",
        "email": email,
        "rate_limit": {
            "limit_per_minute": ONBOARDING_LIMIT_PER_MINUTE,
            "remaining": remaining
        }
    })
    response.headers["X-RateLimit-Limit"] = str(ONBOARDING_LIMIT_PER_MINUTE)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response, 200


@app.route('/api/payments/webhook/connector', methods=['POST'])
def payments_webhook_connector():
    payload = request.get_json(silent=True) or {}
    webhook_url = payload.get("webhook_url")
    if not webhook_url:
        return jsonify({
            "status": "error",
            "message": "Missing required field: webhook_url"
        }), 400

    job_id = str(uuid.uuid4())
    connector_payload = {
        "event": payload.get("event", "payment.confirmed"),
        "payment_id": payload.get("payment_id"),
        "amount": payload.get("amount"),
        "currency": payload.get("currency", "USD"),
        "timestamp": int(time.time())
    }

    with payments_webhook_jobs_lock:
        payments_webhook_jobs[job_id] = {
            "status": "queued",
            "created_at": int(time.time()),
            "attempts": 0,
            "webhook_url": webhook_url,
            "timeout_seconds": PAYMENTS_WEBHOOK_TIMEOUT_SECONDS,
            "max_retries": PAYMENTS_WEBHOOK_MAX_RETRIES
        }

    payments_webhook_executor.submit(_run_payments_webhook_job, job_id, webhook_url, connector_payload)

    return jsonify({
        "status": "accepted",
        "message": "Payments webhook dispatch queued.",
        "job_id": job_id,
        "connector": {
            "timeout_seconds": PAYMENTS_WEBHOOK_TIMEOUT_SECONDS,
            "retry_policy": {
                "max_retries": PAYMENTS_WEBHOOK_MAX_RETRIES,
                "backoff": "exponential",
                "base_delay_seconds": PAYMENTS_WEBHOOK_BACKOFF_BASE_SECONDS
            }
        }
    }), 202


@app.route('/api/payments/webhook/connector/<job_id>', methods=['GET'])
def payments_webhook_connector_job_status(job_id):
    with payments_webhook_jobs_lock:
        job = payments_webhook_jobs.get(job_id)

    if not job:
        return jsonify({
            "status": "error",
            "message": "Job not found"
        }), 404

    return jsonify(job), 200


@app.route('/api/email/smtp/test', methods=['POST'])
def smtp_test_connection():
    config = _load_smtp_config()
    missing = [
        field_name for field_name in ("host", "user", "password")
        if not config[field_name]
    ]
    if missing:
        return jsonify({
            "status": "error",
            "message": "Missing SMTP configuration fields",
            "missing": missing,
        }), 400

    try:
        with _smtp_connect(config) as smtp_client:
            smtp_client.ehlo()
            _smtp_login_if_needed(smtp_client, config)

        return jsonify({
            "status": "ok",
            "message": "SMTP credentials and transport are valid.",
            "config": {
                "host": config["host"],
                "port": config["port"],
                "use_tls": config["use_tls"],
                "use_ssl": config["use_ssl"],
                "timeout_seconds": config["timeout_seconds"],
            },
        }), 200
    except (smtplib.SMTPException, socket.timeout, OSError, ValueError) as smtp_error:
        smtp_code, smtp_message = _parse_smtp_error(smtp_error)
        return jsonify({
            "status": "error",
            "message": "SMTP connectivity/authentication test failed",
            "smtp_error": {
                "code": smtp_code,
                "message": smtp_message,
            },
        }), 502


@app.route('/api/email/send', methods=['POST'])
def smtp_send_email():
    payload = request.get_json(silent=True) or {}
    required_fields = ["to_email", "subject", "body"]
    missing = [field_name for field_name in required_fields if not payload.get(field_name)]
    if missing:
        return jsonify({
            "status": "error",
            "message": "Missing required fields",
            "missing": missing,
        }), 400

    config = _load_smtp_config()
    from_email = payload.get("from_email") or config.get("user")
    if not from_email:
        return jsonify({
            "status": "error",
            "message": "Missing sender email. Provide from_email or SMTP_USER.",
        }), 400

    job_id = str(uuid.uuid4())
    email_payload = {
        "from_email": from_email,
        "to_email": payload["to_email"],
        "subject": payload["subject"],
        "body": payload["body"],
    }

    with smtp_jobs_lock:
        smtp_jobs[job_id] = {
            "status": "queued",
            "created_at": int(time.time()),
            "attempts": 0,
            "to_email": email_payload["to_email"],
            "retry_limit": SMTP_RETRY_LIMIT,
            "timeout_seconds": config["timeout_seconds"],
            "transport": {
                "host": config["host"],
                "port": config["port"],
                "use_tls": config["use_tls"],
                "use_ssl": config["use_ssl"],
            },
        }

    smtp_executor.submit(_run_smtp_job, job_id, email_payload)

    return jsonify({
        "status": "accepted",
        "message": "Email queued for async SMTP delivery.",
        "job_id": job_id,
        "retry_policy": {
            "max_retries": SMTP_RETRY_LIMIT,
            "backoff": "exponential",
            "base_delay_seconds": SMTP_BACKOFF_BASE_SECONDS,
        },
    }), 202


@app.route('/api/email/send/<job_id>', methods=['GET'])
def smtp_send_email_status(job_id):
    with smtp_jobs_lock:
        job = smtp_jobs.get(job_id)

    if not job:
        return jsonify({
            "status": "error",
            "message": "Job not found",
        }), 404

    return jsonify(job), 200

# Serving any other image
@app.route('/<path:path>', methods=['GET'])
def serve_any_other_file(path):
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = os.path.join(path, 'index.html')
    response = send_from_directory(static_file_dir, path)
    response.cache_control.max_age = 0 # avoid cache memory
    return response

if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=_env_int('FLASK_PORT', 3000),
        debug=os.getenv('FLASK_DEBUG', 'true').lower() in ('1', 'true', 'yes', 'on'),
        extra_files=['./',]
    )

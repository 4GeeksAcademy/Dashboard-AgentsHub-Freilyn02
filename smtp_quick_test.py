import os
import smtplib
import socket
import ssl
import sys


def env_bool(name, default):
    value = os.getenv(name, default)
    return str(value).lower() in ("1", "true", "yes", "on")


def main():
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    use_tls = env_bool("SMTP_USE_TLS", "true")
    use_ssl = env_bool("SMTP_USE_SSL", "false")
    timeout_seconds = int(os.getenv("SMTP_TIMEOUT_SECONDS", "15"))

    missing = [name for name, value in (
        ("SMTP_HOST", host),
        ("SMTP_USER", user),
        ("SMTP_PASS", password),
    ) if not value]
    if missing:
        print(f"[error] Missing environment variables: {', '.join(missing)}")
        return 1

    try:
        if use_ssl:
            context = ssl.create_default_context()
            smtp = smtplib.SMTP_SSL(host, port, timeout=timeout_seconds, context=context)
        else:
            smtp = smtplib.SMTP(host, port, timeout=timeout_seconds)

        with smtp:
            smtp.ehlo()
            if use_tls and not use_ssl:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(user, password)

        print("[ok] SMTP connectivity and authentication validated")
        print(f"host={host} port={port} use_tls={use_tls} use_ssl={use_ssl} timeout={timeout_seconds}s")
        return 0
    except smtplib.SMTPResponseException as smtp_error:
        code = smtp_error.smtp_code
        message = smtp_error.smtp_error.decode("utf-8", errors="replace") if isinstance(smtp_error.smtp_error, bytes) else str(smtp_error.smtp_error)
        print(f"[error] SMTP response error code={code} message={message}")
        return 2
    except (smtplib.SMTPException, socket.timeout, OSError, ValueError) as error:
        print(f"[error] SMTP test failed: {error}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

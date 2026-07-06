import smtplib
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import server


class TestNovaOnboardingRateLimit(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.original_limit = server.ONBOARDING_LIMIT_PER_MINUTE
        self.original_window = server.ONBOARDING_WINDOW_SECONDS
        server.ONBOARDING_LIMIT_PER_MINUTE = 5
        server.ONBOARDING_WINDOW_SECONDS = 60
        with server.onboarding_rate_limit_lock:
            server.onboarding_rate_limit_store.clear()

    def tearDown(self):
        server.ONBOARDING_LIMIT_PER_MINUTE = self.original_limit
        server.ONBOARDING_WINDOW_SECONDS = self.original_window
        with server.onboarding_rate_limit_lock:
            server.onboarding_rate_limit_store.clear()

    def _send_onboarding_request(self):
        response = self.client.post(
            "/api/onboarding/register",
            json={"email": "nova-load@example.com"},
            headers={"X-Forwarded-For": "10.0.0.1"},
        )
        return response.status_code

    def test_onboarding_concurrent_burst_respects_limit(self):
        total_requests = 10
        with ThreadPoolExecutor(max_workers=total_requests) as executor:
            status_codes = list(executor.map(lambda _: self._send_onboarding_request(), range(total_requests)))

        self.assertEqual(status_codes.count(200), server.ONBOARDING_LIMIT_PER_MINUTE)
        self.assertEqual(status_codes.count(429), total_requests - server.ONBOARDING_LIMIT_PER_MINUTE)


class TestAtlasPaymentsWebhookRetryPolicy(unittest.TestCase):
    def setUp(self):
        with server.payments_webhook_jobs_lock:
            server.payments_webhook_jobs.clear()

    def test_payments_connector_retries_with_exponential_backoff_before_warning(self):
        job_id = "atlas-retry-job"
        with server.payments_webhook_jobs_lock:
            server.payments_webhook_jobs[job_id] = {
                "status": "queued",
                "created_at": 0,
                "attempts": 0,
            }

        with patch.object(server, "_post_json_with_timeout", side_effect=TimeoutError("mock timeout")) as mock_post:
            with patch.object(server.time, "sleep") as mock_sleep:
                server._run_payments_webhook_job(job_id, "http://mock-payments", {"event": "payment.confirmed"})

        expected_attempts = server.PAYMENTS_WEBHOOK_MAX_RETRIES + 1
        self.assertEqual(mock_post.call_count, expected_attempts)

        expected_backoff = [server.PAYMENTS_WEBHOOK_BACKOFF_BASE_SECONDS * (2 ** i) for i in range(server.PAYMENTS_WEBHOOK_MAX_RETRIES)]
        actual_backoff = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertEqual(actual_backoff, expected_backoff)

        with server.payments_webhook_jobs_lock:
            job = server.payments_webhook_jobs[job_id]

        self.assertEqual(job["status"], "warning")
        self.assertEqual(job["attempts"], expected_attempts)
        self.assertIn("Timeout in payments webhook connector", job["warning"])


class TestEchoSmtpAuthFailureHandling(unittest.TestCase):
    def setUp(self):
        with server.smtp_jobs_lock:
            server.smtp_jobs.clear()

    def test_smtp_auth_error_logs_once_and_stops_retry_loop(self):
        job_id = "echo-auth-fail-job"
        with server.smtp_jobs_lock:
            server.smtp_jobs[job_id] = {
                "status": "queued",
                "created_at": 0,
                "attempts": 0,
            }

        email_payload = {
            "from_email": "no-reply@agenthub.io",
            "to_email": "user@example.com",
            "subject": "Payment update",
            "body": "Your payment is being processed.",
        }

        auth_error = smtplib.SMTPAuthenticationError(535, b"Authentication failed")

        with patch.object(server, "_send_smtp_message", side_effect=auth_error) as mock_send:
            with patch.object(server.time, "sleep") as mock_sleep:
                with patch("builtins.print") as mock_print:
                    server._run_smtp_job(job_id, email_payload)

        self.assertEqual(mock_send.call_count, 1)
        mock_sleep.assert_not_called()

        with server.smtp_jobs_lock:
            job = server.smtp_jobs[job_id]

        self.assertEqual(job["status"], "warning")
        self.assertEqual(job["attempts"], 1)
        self.assertEqual(job["smtp_error"]["code"], 535)
        self.assertTrue(job["smtp_error"]["non_retryable"])

        log_lines = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
        self.assertTrue(any("SMTP retry limit exceeded" in line for line in log_lines))


if __name__ == "__main__":
    unittest.main()

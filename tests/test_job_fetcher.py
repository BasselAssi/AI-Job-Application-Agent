import socket
import unittest
from unittest.mock import patch

import httpx

from job_fetcher import JobFetchError, fetch_job_posting


PUBLIC_DNS_RESULT = [
    (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
]


class FetchJobPostingTests(unittest.TestCase):
    def setUp(self):
        self.dns_patcher = patch(
            "job_fetcher.socket.getaddrinfo",
            return_value=PUBLIC_DNS_RESULT,
        )
        self.dns_patcher.start()
        self.addCleanup(self.dns_patcher.stop)

    def fetch_with_response(self, handler, url="https://jobs.example.test/job"):
        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        client_factory = patch("job_fetcher.httpx.Client", return_value=client)
        with client_factory:
            return fetch_job_posting(url)

    def test_extracts_readable_main_text_and_ignores_scripts(self):
        def handler(request):
            return httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text=(
                    "<html><head><title>Architect role</title>"
                    "<script>ignore this</script></head>"
                    "<body><main><h1>AI Solution Architect</h1>"
                    "<p>Design cloud solutions.</p></main></body></html>"
                ),
            )

        text = self.fetch_with_response(handler)

        self.assertIn("Architect role", text)
        self.assertIn("AI Solution Architect", text)
        self.assertIn("Design cloud solutions.", text)
        self.assertNotIn("ignore this", text)

    def test_prefers_job_description_container_over_site_navigation(self):
        def handler(request):
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=(
                    "<html><body><nav>Navigation and cookie settings</nav>"
                    "<div class='joblayouttoken'>"
                    "<h1>AI Solution Architect</h1>"
                    "<p>Design enterprise AI solutions.</p>"
                    "</div></body></html>"
                ),
            )

        text = self.fetch_with_response(handler)

        self.assertIn("AI Solution Architect", text)
        self.assertIn("Design enterprise AI solutions.", text)
        self.assertNotIn("Navigation and cookie settings", text)

    def test_follows_public_redirects(self):
        def handler(request):
            if request.url.path == "/job":
                return httpx.Response(302, headers={"location": "/posting"})
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<main>Job description</main>",
            )

        self.assertIn("Job description", self.fetch_with_response(handler))

    def test_rejects_non_http_url(self):
        with self.assertRaisesRegex(JobFetchError, "public HTTP or HTTPS"):
            fetch_job_posting("file:///etc/passwd")

    def test_rejects_private_dns_addresses(self):
        with patch(
            "job_fetcher.socket.getaddrinfo",
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))
            ],
        ):
            with self.assertRaisesRegex(JobFetchError, "non-public addresses"):
                fetch_job_posting("https://localhost/job")

    def test_rejects_redirects_to_private_addresses(self):
        def resolve(host, port, type):
            address = "127.0.0.1" if host == "127.0.0.1" else "93.184.216.34"
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, port))]

        def handler(request):
            return httpx.Response(
                302,
                headers={"location": "http://127.0.0.1/internal"},
            )

        with patch("job_fetcher.socket.getaddrinfo", side_effect=resolve):
            with self.assertRaisesRegex(JobFetchError, "non-public addresses"):
                self.fetch_with_response(handler)

    def test_enforces_response_size_limit(self):
        def handler(request):
            return httpx.Response(
                200,
                headers={
                    "content-type": "text/html",
                    "content-length": "2000001",
                },
                text="",
            )

        with self.assertRaisesRegex(JobFetchError, "2 MB limit"):
            self.fetch_with_response(handler)


if __name__ == "__main__":
    unittest.main()

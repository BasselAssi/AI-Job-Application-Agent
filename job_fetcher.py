import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup


MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 5
REQUEST_TIMEOUT_SECONDS = 10.0
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class JobFetchError(Exception):
    """An expected error while retrieving or extracting a job posting."""


def _validate_public_http_url(url: str) -> str:
    try:
        parsed_url = urlsplit(url.strip())
        hostname = parsed_url.hostname
        port = parsed_url.port
    except ValueError as error:
        raise JobFetchError("The job posting URL is invalid.") from error

    if (
        parsed_url.scheme not in {"http", "https"}
        or not hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
    ):
        raise JobFetchError("Use a public HTTP or HTTPS job posting URL.")

    expected_port = 443 if parsed_url.scheme == "https" else 80
    if port is not None and port != expected_port:
        raise JobFetchError("Only the standard HTTP and HTTPS ports are allowed.")

    try:
        addresses = socket.getaddrinfo(
            hostname,
            port or expected_port,
            type=socket.SOCK_STREAM,
        )
    except OSError as error:
        raise JobFetchError("The job posting host could not be resolved.") from error

    if not addresses:
        raise JobFetchError("The job posting host did not resolve to an address.")

    for address in addresses:
        try:
            ip_address = ipaddress.ip_address(address[4][0].split("%", 1)[0])
        except ValueError as error:
            raise JobFetchError("The job posting host resolved to an invalid address.") from error
        if not ip_address.is_global:
            raise JobFetchError("For safety, URLs resolving to non-public addresses are blocked.")

    return url.strip()


def _extract_page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()

    content = soup.find(["main", "article"]) or soup.find(attrs={"role": "main"})
    if not content:
        content_classes = (
            "joblayouttoken",
            "job-description",
            "jobdescription",
            "job-details",
            "jobdetails",
            "posting-description",
            "postingdescription",
        )
        for class_name in content_classes:
            content = soup.find(
                attrs={
                    "class": lambda value: value
                    and class_name in " ".join(value if isinstance(value, list) else [value]).lower()
                }
            )
            if content:
                break

    content = content or soup.body or soup
    text = " ".join(content.stripped_strings)
    if title and title not in text:
        text = f"{title}\n\n{text}" if text else title

    return text


def fetch_job_posting(url: str) -> str:
    """Fetch a public HTML page and return its readable text."""
    current_url = _validate_public_http_url(url)

    try:
        with httpx.Client(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": "JobApplicationAssistant/0.1"},
        ) as client:
            for redirect_count in range(MAX_REDIRECTS + 1):
                current_url = _validate_public_http_url(current_url)
                with client.stream("GET", current_url) as response:
                    if response.status_code in REDIRECT_STATUSES:
                        location = response.headers.get("location")
                        if not location:
                            raise JobFetchError("The job page redirected without a destination.")
                        if redirect_count == MAX_REDIRECTS:
                            raise JobFetchError("The job page redirected too many times.")
                        current_url = urljoin(current_url, location)
                        continue

                    if response.status_code >= 400:
                        raise JobFetchError(
                            f"The job site returned HTTP {response.status_code}."
                        )

                    content_type = response.headers.get("content-type", "").lower()
                    if content_type and not (
                        content_type.startswith("text/html")
                        or content_type.startswith("application/xhtml+xml")
                    ):
                        raise JobFetchError("The job URL did not return an HTML page.")

                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            declared_length = int(content_length)
                        except ValueError as error:
                            raise JobFetchError(
                                "The job page returned an invalid content length."
                            ) from error
                        if declared_length > MAX_RESPONSE_BYTES:
                            raise JobFetchError("The job page is larger than the 2 MB limit.")

                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise JobFetchError("The job page is larger than the 2 MB limit.")

                    html = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                    page_text = _extract_page_text(html)
                    if not page_text:
                        raise JobFetchError(
                            "No readable text was found. Paste the job description instead."
                        )
                    return page_text

    except httpx.TimeoutException as error:
        raise JobFetchError("The job site took too long to respond.") from error
    except httpx.HTTPError as error:
        raise JobFetchError(f"Could not retrieve the job page: {error}") from error

    raise JobFetchError("The job page could not be retrieved.")

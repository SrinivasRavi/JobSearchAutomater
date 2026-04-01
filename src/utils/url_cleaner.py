"""URL cleaning utility for dedupe keys."""
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs


def clean_job_link(url: str, keep_params: list[str] | None = None) -> str:
    if not url:
        return ""

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    if keep_params:
        original_params = parse_qs(parsed.query, keep_blank_values=False)
        filtered = {k: original_params[k][0] for k in keep_params if k in original_params}
        query = urlencode(filtered)
    else:
        query = ""

    return urlunparse((scheme, netloc, path, "", query, ""))

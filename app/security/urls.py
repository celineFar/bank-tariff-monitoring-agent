import ipaddress
from urllib.parse import urlsplit


class DisallowedSourceUrl(ValueError):
    pass


def validate_source_url(url: str, allowed_hosts: tuple[str, ...]) -> str:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise DisallowedSourceUrl("Source URL must use HTTPS and include a host")
    host = parsed.hostname.lower().rstrip(".")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise DisallowedSourceUrl("IP-literal source URLs are not allowed")
    if host not in {item.lower().rstrip(".") for item in allowed_hosts}:
        raise DisallowedSourceUrl(f"Source host is not allowlisted: {host}")
    if parsed.username or parsed.password:
        raise DisallowedSourceUrl("Source URL credentials are not allowed")
    return parsed.geturl()

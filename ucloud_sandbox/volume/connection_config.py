import logging
import os

from typing import Dict, Optional, TypedDict

from typing_extensions import Unpack

from ucloud_sandbox.api.metadata import package_version
from ucloud_sandbox.domain_config import get_ucloud_sandbox_domain
from ucloud_sandbox.connection_config import ProxyTypes

REQUEST_TIMEOUT: float = 60.0  # 60 seconds

# Timeout for volume file transfers, which stream large bodies and so must not
# inherit the short REQUEST_TIMEOUT. (Sandbox filesystem streaming instead
# bounds each chunk by the request timeout and leaves the total to the server.)
FILE_TIMEOUT: float = 3600.0  # 1 hour

# Idle bound for every read on the volume content transports: the transfer is
# aborted when no bytes at all arrive for this long. It resets on each chunk,
# so it never limits total transfer time — only a fully stalled connection.
# Matches the JS SDK's default stream idle timeout (REQUEST_TIMEOUT_MS).
#
# Kept equal to `e2b.connection_config.READ_TIMEOUT` on purpose: the read bound
# is part of the transport cache key, so the volume streaming pool shares the
# sandbox-filesystem streaming pool only while the two constants agree. Change
# one and they silently split into two reqwest pools.
READ_TIMEOUT: float = 60.0  # 60 seconds


class VolumeApiParams(TypedDict, total=False):
    """
    Parameters for requests made to the volume content API.
    """

    domain: Optional[str]
    """Domain to use for the volume API, defaults to `UCLOUD_SANDBOX_REGION`, `UCLOUD_SANDBOX_DOMAIN`, or the default UCloud Sandbox domain."""

    debug: Optional[bool]
    """Whether to use debug mode, defaults to `UCLOUD_SANDBOX_DEBUG` environment variable."""

    insecure_http: Optional[bool]
    """Whether to use HTTP instead of HTTPS, defaults to `UCLOUD_SANDBOX_INSECURE_HTTP`."""

    request_timeout: Optional[float]
    """Timeout for the request in **seconds**, defaults to 60 seconds."""

    headers: Optional[Dict[str, str]]
    """Additional headers to send with the request."""

    token: Optional[str]
    """Volume auth token used for `Authorization: Bearer <token>`."""

    api_url: Optional[str]
    """URL to use for the volume API, defaults to `UCLOUD_SANDBOX_VOLUME_API_URL` or `<protocol>://api.<domain>`."""

    proxy: Optional[ProxyTypes]
    """Proxy to use for the request."""

    logger: Optional[logging.Logger]
    """Logger used for request and response logging. Accepts a standard library `logging.Logger`."""


class VolumeConnectionConfig:
    """
    Configuration for the volume content API.

    Uses bearer token authentication and defaults to the volume content host.
    """

    @staticmethod
    def _domain():
        return get_ucloud_sandbox_domain()

    @staticmethod
    def _debug():
        return os.getenv("UCLOUD_SANDBOX_DEBUG", "false").lower() == "true"

    @staticmethod
    def _volume_api_url():
        return os.getenv("UCLOUD_SANDBOX_VOLUME_API_URL")

    @staticmethod
    def _insecure_http():
        return os.getenv("UCLOUD_SANDBOX_INSECURE_HTTP", "false").lower() == "true"

    @staticmethod
    def _get_request_timeout(
        default_timeout: Optional[float],
        request_timeout: Optional[float],
    ):
        if request_timeout == 0:
            return None
        elif request_timeout is not None:
            return request_timeout
        else:
            return default_timeout

    def __init__(
        self,
        domain: Optional[str] = None,
        debug: Optional[bool] = None,
        insecure_http: Optional[bool] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
        request_timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        proxy: Optional[ProxyTypes] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger
        self.domain = domain or self._domain()
        self.debug = debug if debug is not None else self._debug()
        self.insecure_http = (
            True
            if self.debug
            else (
                insecure_http
                if insecure_http is not None
                else self._insecure_http()
            )
        )
        protocol = "http" if self.insecure_http else "https"

        self.api_url = (
            api_url
            or self._volume_api_url()
            or (
                "http://localhost:8080"
                if self.debug
                else f"{protocol}://api.{self.domain}"
            )
        )
        self.access_token = token
        self.token = self.access_token
        self.proxy = proxy

        self.headers = dict(headers) if headers else {}
        self.headers["User-Agent"] = f"ucloud-agentbox-sdk/{package_version}"

        self.request_timeout = self._get_request_timeout(
            REQUEST_TIMEOUT, request_timeout
        )

    def get_request_timeout(self, request_timeout: Optional[float] = None):
        return self._get_request_timeout(self.request_timeout, request_timeout)

    def get_api_params(
        self,
        **opts: Unpack[VolumeApiParams],
    ) -> dict:
        """
        Get request parameters for the volume content API.
        """
        domain = opts.get("domain")
        debug = opts.get("debug")
        insecure_http = opts.get("insecure_http")
        headers = opts.get("headers")
        request_timeout = opts.get("request_timeout")
        token = opts.get("token")
        api_url = opts.get("api_url")
        proxy = opts.get("proxy")
        logger = opts.get("logger")

        req_headers = self.headers.copy()
        if headers is not None:
            req_headers.update(headers)

        return dict(
            VolumeApiParams(
                domain=domain if domain is not None else self.domain,
                debug=debug if debug is not None else self.debug,
                insecure_http=(
                    insecure_http
                    if insecure_http is not None
                    else self.insecure_http
                ),
                token=token if token is not None else self.token,
                api_url=api_url if api_url is not None else self.api_url,
                request_timeout=self.get_request_timeout(request_timeout),
                headers=req_headers,
                proxy=proxy if proxy is not None else self.proxy,
                logger=logger if logger is not None else self.logger,
            )
        )

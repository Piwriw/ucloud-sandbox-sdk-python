import inspect

from packaging.version import Version

from ucloud_sandbox.code_interpreter import code_interpreter_async, code_interpreter_sync
from ucloud_sandbox.code_interpreter.constants import JUPYTER_PORT
from ucloud_sandbox.connection_config import ConnectionConfig
from ucloud_sandbox.desktop import main as desktop_main
from ucloud_sandbox.domain_config import (
    get_default_base_image,
    get_ucloud_sandbox_domain,
    is_region_cn,
)
from ucloud_sandbox.sandbox.main import SandboxBase
from ucloud_sandbox.volume.connection_config import VolumeConnectionConfig
from ucloud_sandbox.volume.volume_async import AsyncVolume
from ucloud_sandbox.volume.volume_sync import Volume


def _sandbox(**config_opts) -> SandboxBase:
    return SandboxBase(
        sandbox_id="sandbox-id",
        sandbox_domain="private.example",
        envd_version=Version("0.1.0"),
        envd_access_token=None,
        traffic_access_token=None,
        connection_config=ConnectionConfig(
            domain="private.example", **config_opts
        ),
    )


def test_region_env_overrides_domain_env(monkeypatch):
    monkeypatch.setenv("UCLOUD_SANDBOX_REGION", "cn-bj")
    monkeypatch.setenv("UCLOUD_SANDBOX_DOMAIN", "custom.example")
    monkeypatch.delenv("UCLOUD_SANDBOX_API_URL", raising=False)

    config = ConnectionConfig()

    assert get_ucloud_sandbox_domain() == "cn-bj.sandbox.ucloudai.com"
    assert config.domain == "cn-bj.sandbox.ucloudai.com"
    assert config.api_url == "https://api.cn-bj.sandbox.ucloudai.com"


def test_explicit_domain_has_priority_over_region_env(monkeypatch):
    monkeypatch.setenv("UCLOUD_SANDBOX_REGION", "cn-bj")

    config = ConnectionConfig(domain="custom.example")

    assert config.domain == "custom.example"
    assert config.api_url == "https://api.custom.example"


def test_volume_config_uses_region_env(monkeypatch):
    monkeypatch.setenv("UCLOUD_SANDBOX_REGION", "cn-sh2")
    monkeypatch.setenv("UCLOUD_SANDBOX_DOMAIN", "custom.example")
    monkeypatch.delenv("UCLOUD_SANDBOX_VOLUME_API_URL", raising=False)

    config = VolumeConnectionConfig()

    assert config.domain == "cn-sh2.sandbox.ucloudai.com"
    assert config.api_url == "https://api.cn-sh2.sandbox.ucloudai.com"


def test_insecure_http_supports_all_sandbox_urls(monkeypatch):
    monkeypatch.delenv("UCLOUD_SANDBOX_INSECURE_HTTP", raising=False)
    config = ConnectionConfig(
        domain="private.example",
        api_url="http://api.private.example",
        insecure_http=True,
    )

    sandbox = SandboxBase(
        sandbox_id="sandbox-id",
        sandbox_domain="private.example",
        envd_version=Version("0.1.0"),
        envd_access_token=None,
        traffic_access_token=None,
        connection_config=config,
    )

    assert config.api_url == "http://api.private.example"
    assert sandbox.envd_api_url == "http://49983-sandbox-id.private.example"
    assert sandbox.get_url(8080, "/health") == (
        "http://8080-sandbox-id.private.example/health"
    )
    assert sandbox.get_mcp_url() == "http://50005-sandbox-id.private.example/mcp"


def test_insecure_http_uses_environment(monkeypatch):
    monkeypatch.setenv("UCLOUD_SANDBOX_INSECURE_HTTP", "true")

    config = ConnectionConfig(domain="private.example")
    volume_config = VolumeConnectionConfig(domain="private.example")

    assert config.insecure_http is True
    assert config.sandbox_protocol == "http"
    assert config.api_url == "http://api.private.example"
    assert config.get_sandbox_url("sandbox-id", "private.example") == (
        "http://49983-sandbox-id.private.example"
    )
    assert volume_config.insecure_http is True
    assert volume_config.api_url == "http://api.private.example"


def test_secure_https_is_the_default(monkeypatch):
    monkeypatch.delenv("UCLOUD_SANDBOX_INSECURE_HTTP", raising=False)

    config = ConnectionConfig(domain="private.example")

    assert config.insecure_http is False
    assert config.sandbox_protocol == "https"
    assert config.api_url == "https://api.private.example"


def test_explicit_secure_http_setting_overrides_environment(monkeypatch):
    monkeypatch.setenv("UCLOUD_SANDBOX_INSECURE_HTTP", "true")

    config = ConnectionConfig(domain="private.example", insecure_http=False)

    assert config.insecure_http is False
    assert config.api_url == "https://api.private.example"


def test_insecure_http_is_propagated_to_per_call_config(monkeypatch):
    monkeypatch.delenv("UCLOUD_SANDBOX_INSECURE_HTTP", raising=False)
    config = ConnectionConfig(domain="private.example", insecure_http=True)

    per_call_config = ConnectionConfig(**config.get_api_params())

    assert per_call_config.insecure_http is True
    assert per_call_config.api_url == "http://api.private.example"
    assert per_call_config.get_sandbox_url("sandbox-id", "private.example") == (
        "http://49983-sandbox-id.private.example"
    )


def test_jupyter_url_follows_sandbox_protocol(monkeypatch):
    """
    The code interpreter must resolve the Jupyter URL through `get_url` rather
    than hardcoding https, otherwise `insecure_http` silently stops applying to
    it. The hack that rewrites this is easy to lose on an upstream sync, so
    assert on the source of both the sync and async variants.
    """
    monkeypatch.delenv("UCLOUD_SANDBOX_INSECURE_HTTP", raising=False)

    for cls in (code_interpreter_sync.Sandbox, code_interpreter_async.AsyncSandbox):
        source = inspect.getsource(cls._jupyter_url.fget)
        assert "return self.get_url(JUPYTER_PORT)" in source
        assert "https" not in source

    insecure = _sandbox(insecure_http=True)
    assert insecure.get_url(JUPYTER_PORT) == (
        f"http://{JUPYTER_PORT}-sandbox-id.private.example"
    )
    assert _sandbox().get_url(JUPYTER_PORT) == (
        f"https://{JUPYTER_PORT}-sandbox-id.private.example"
    )


def test_desktop_vnc_url_follows_sandbox_protocol(monkeypatch):
    """Same guard for the desktop VNC URL."""
    monkeypatch.delenv("UCLOUD_SANDBOX_INSECURE_HTTP", raising=False)

    source = inspect.getsource(desktop_main)
    assert 'get_url(self._port, "/vnc.html")' in source
    assert "https://{desktop.get_host" not in source
    assert "https://{self.__desktop.get_host" not in source

    assert _sandbox(insecure_http=True).get_url(6080, "/vnc.html") == (
        "http://6080-sandbox-id.private.example/vnc.html"
    )
    assert _sandbox().get_url(6080, "/vnc.html") == (
        "https://6080-sandbox-id.private.example/vnc.html"
    )


def test_default_base_image_follows_region(monkeypatch):
    monkeypatch.setenv("UCLOUD_SANDBOX_REGION", "cn-bj")
    assert is_region_cn() is True
    assert get_default_base_image().endswith("/base_cn:latest")

    monkeypatch.setenv("UCLOUD_SANDBOX_REGION", "gray-test")
    assert is_region_cn() is True

    monkeypatch.setenv("UCLOUD_SANDBOX_REGION", "hk-01")
    assert is_region_cn() is False
    assert get_default_base_image().endswith("/base:latest")

    # The default region is a CN one.
    monkeypatch.delenv("UCLOUD_SANDBOX_REGION", raising=False)
    assert get_default_base_image().endswith("/base_cn:latest")


def test_volume_instances_preserve_insecure_http_setting(monkeypatch):
    monkeypatch.delenv("UCLOUD_SANDBOX_INSECURE_HTTP", raising=False)
    volume = Volume(
        volume_id="volume-id",
        name="volume",
        domain="private.example",
        insecure_http=True,
    )
    async_volume = AsyncVolume(
        volume_id="volume-id",
        name="volume",
        domain="private.example",
        insecure_http=True,
    )

    assert volume._get_volume_config().api_url == "http://api.private.example"
    assert async_volume._get_volume_config().api_url == "http://api.private.example"

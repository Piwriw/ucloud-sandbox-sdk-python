import os


DEFAULT_REGION = "cn-wlcb"
DEFAULT_DOMAIN = f"{DEFAULT_REGION}.sandbox.ucloudai.com"
REGION_ENV_VAR = "UCLOUD_SANDBOX_REGION"
DOMAIN_ENV_VAR = "UCLOUD_SANDBOX_DOMAIN"
DOMAIN_SUFFIX = "sandbox.ucloudai.com"

CN_BASE_IMAGE = "uhub.service.ucloud.cn/agent-sandbox/base:cn"
DEFAULT_BASE_IMAGE = "uhub.service.ucloud.cn/agent-sandbox/base:latest"
CN_REGION_PREFIXES = ("cn", "gray")


def get_ucloud_sandbox_region() -> str:
    return os.getenv(REGION_ENV_VAR, "").strip() or DEFAULT_REGION


def get_ucloud_sandbox_domain() -> str:
    region = os.getenv(REGION_ENV_VAR, "").strip()
    if region:
        return f"{region}.{DOMAIN_SUFFIX}"

    return os.getenv(DOMAIN_ENV_VAR) or DEFAULT_DOMAIN


def get_default_base_image() -> str:
    if get_ucloud_sandbox_region().lower().startswith(CN_REGION_PREFIXES):
        return CN_BASE_IMAGE

    return DEFAULT_BASE_IMAGE

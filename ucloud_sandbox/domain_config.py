import os

from typing import Optional


DEFAULT_REGION = "cn-wlcb"
DEFAULT_DOMAIN = f"{DEFAULT_REGION}.sandbox.ucloudai.com"
REGION_ENV_VAR = "UCLOUD_SANDBOX_REGION"
DOMAIN_ENV_VAR = "UCLOUD_SANDBOX_DOMAIN"
DOMAIN_SUFFIX = "sandbox.ucloudai.com"

CN_BASE_IMAGE = "uhub.service.ucloud.cn/agent-sandbox-public/base_cn:latest"
DEFAULT_BASE_IMAGE = "uhub.service.ucloud.cn/agent-sandbox-public/base:latest"
CN_REGION_PREFIXES = ("cn", "gray")


def get_ucloud_sandbox_region() -> str:
    return os.getenv(REGION_ENV_VAR, "").strip() or DEFAULT_REGION


def get_ucloud_sandbox_domain() -> str:
    region = os.getenv(REGION_ENV_VAR, "").strip()
    if region:
        return f"{region}.{DOMAIN_SUFFIX}"

    return os.getenv(DOMAIN_ENV_VAR) or DEFAULT_DOMAIN


def is_region_cn(region: Optional[str] = None) -> bool:
    """
    Whether the region is a CN region.

    :param region: Region to check, defaults to the currently configured region
    :return: `True` for regions starting with "cn" or "gray"
    """
    if region is None:
        region = get_ucloud_sandbox_region()

    return region.strip().lower().startswith(CN_REGION_PREFIXES)


def get_default_base_image() -> str:
    if is_region_cn():
        return CN_BASE_IMAGE

    return DEFAULT_BASE_IMAGE

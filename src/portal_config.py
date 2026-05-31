"""
MANAK portal base URLs — Live vs Demo (UAT).
HallmarkPro API URLs (hallmarkpro.in) are separate and unchanged.
"""

PORTAL_ENV_LIVE = "live"
PORTAL_ENV_DEMO = "demo"

PORTAL_BASE_URLS = {
    PORTAL_ENV_LIVE: "https://huid.manakonline.in",
    PORTAL_ENV_DEMO: "https://newmanak.uat.dcservices.in",
}

ALL_PORTAL_BASES = tuple(PORTAL_BASE_URLS.values())

DEFAULT_PORTAL_ENV = PORTAL_ENV_LIVE

_current_env = DEFAULT_PORTAL_ENV

# Default portal paths (same on live and demo; only host changes)
LOGIN_PATH = "/MANAK/eBISLogin"
PORTAL_GENERATE_PATH = (
    "/MANAK/AHC_RequestSubmission"
    "?cml_no=Q1JPL1JBSEMvUi0xMTAwNTg=&outletid=Mg==&EbranchId=OA=="
    "&requestno=&outletname=TUFIQUxBWE1JIEhBTExNQVJLIENFTlRSRQ=="
)


def get_portal_env():
    return _current_env


def set_portal_env(env):
    global _current_env
    if env in PORTAL_BASE_URLS:
        _current_env = env


def get_portal_base_url(env=None):
    env = env or _current_env
    return PORTAL_BASE_URLS.get(env, PORTAL_BASE_URLS[PORTAL_ENV_LIVE])


def build_portal_url(path, env=None):
    """Build full URL: base + path (path should start with /)."""
    base = get_portal_base_url(env).rstrip("/")
    if not path:
        return base
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def swap_portal_base_in_url(url, env=None):
    """Replace live/demo host in a saved URL with the selected environment."""
    if not url or not isinstance(url, str):
        return url
    url = url.strip()
    target = get_portal_base_url(env).rstrip("/")
    for base in ALL_PORTAL_BASES:
        b = base.rstrip("/")
        if url.startswith(b):
            rest = url[len(b) :]
            if rest and not rest.startswith("/"):
                rest = "/" + rest
            return target + (rest or "")
    return url


def get_default_login_url(env=None):
    return build_portal_url(LOGIN_PATH, env)


def get_default_portal_generate_url(env=None):
    return build_portal_url(PORTAL_GENERATE_PATH, env)


def portal_base():
    """Shorthand for f-strings: f'{portal_base()}/MANAK/...'"""
    return get_portal_base_url().rstrip("/")

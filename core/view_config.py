import os


_FALSE_VALUES = {"0", "false", "no", "off", "disabled"}


def components_v2_enabled() -> bool:
    """Return whether Components v2 views should be used for new interactions.

    Supported environment variables:
    - `ROLEBYPOST_COMPONENTS_V2`
    - `COMPONENTS_V2_ENABLED`

    Defaults to enabled when neither flag is set.
    """
    raw_value = os.getenv("ROLEBYPOST_COMPONENTS_V2")
    if raw_value is None:
        raw_value = os.getenv("COMPONENTS_V2_ENABLED")

    if raw_value is None:
        return True

    return raw_value.strip().lower() not in _FALSE_VALUES


def prefer_components_v2(requested: bool = True) -> bool:
    """Combine an explicit V2 request with the global fallback flag."""
    return bool(requested) and components_v2_enabled()
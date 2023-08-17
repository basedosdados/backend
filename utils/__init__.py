from os import getenv as _getenv


def getenv(var, default=None):
    """Get environment variable or raise exception if not set"""
    value = _getenv(var, default)
    if value is None:
        raise ValueError(f"Environment variable {var} not set")
    return value

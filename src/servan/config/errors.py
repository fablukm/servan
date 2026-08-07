"""Configuration error type. Message text is user-facing (shown by cli/)."""


class ConfigError(Exception):
    """Invalid, missing, or inconsistent configuration."""

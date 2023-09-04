"""Module for dealing with feature flags."""
import os
import enum

__all__ = ["FEATURE_ENABLED_VALUE", "FeatureFlag", "is_feature_enabled"]

FEATURE_ENABLED_VALUE = "true"


class FeatureFlag(enum.Enum):
    REPOBEE_4_REVIEW_COMMANDS = "REPOBEE_4_REVIEW_COMMANDS"
    REPOBEE_CORE_COMMANDS_AS_PLUGINS = "REPOBEE_CORE_COMMANDS_AS_PLUGINS"
    REPOBEE_DISABLE_NAME_NORMALIZATION = "REPOBEE_DISABLE_NAME_NORMALIZATION"


def is_feature_enabled(flag: FeatureFlag) -> bool:
    """Check if a feature is enabled.

    Args:
        flag: A feature flag.
    """
    return os.getenv(flag.value) == FEATURE_ENABLED_VALUE

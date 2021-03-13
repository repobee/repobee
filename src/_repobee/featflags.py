"""Module for dealing with feature flags."""
import os
import enum

__all__ = ["FEATURE_ENABLED_VALUE", "FeatureFlag", "is_feature_enabled"]

FEATURE_ENABLED_VALUE = "true"


class FeatureFlag(enum.Enum):
    REPOBEE_4_REVIEW_COMMANDS = "REPOBEE_4_REVIEW_COMMANDS"


def is_feature_enabled(flag: FeatureFlag) -> bool:
    """Check if a feature is enabled.

    Args:
        flag: A feature flag.
    """
    return os.getenv(flag.value) == FEATURE_ENABLED_VALUE

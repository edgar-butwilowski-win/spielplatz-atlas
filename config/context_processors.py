# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.conf import settings


def environment_title_suffix(request):
    """Expose the environment suffix for HTML titles."""

    return {
        "environment_title_suffix": settings.ENVIRONMENT_TITLE_SUFFIX,
        "environment_badge_label": settings.ENVIRONMENT_BADGE_LABEL,
    }

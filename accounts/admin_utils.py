# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

def get_user_organization(user):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return None

    profile = getattr(user, "profile", None)

    if not profile or not profile.is_active_for_organization:
        return None

    return profile.organization
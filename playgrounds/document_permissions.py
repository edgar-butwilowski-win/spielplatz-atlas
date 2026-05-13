# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.


def user_may_view_playground_documents(user, playground):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    return bool(
        profile
        and profile.is_active_for_organization
        and profile.organization_id == playground.organization_id
        and profile.may_view_internal
    )


def user_may_view_playground_document(user, document):
    return user_may_view_playground_documents(user, document.playground)

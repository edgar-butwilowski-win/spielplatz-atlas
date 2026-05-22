# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from accounts.permissions import user_may_view_internal


def user_may_view_playground_documents(user, playground):
    return user_may_view_internal(user, playground.organization)


def user_may_view_playground_document(user, document):
    return user_may_view_playground_documents(user, document.playground)

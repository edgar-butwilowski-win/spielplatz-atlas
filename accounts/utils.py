# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import uuid


def normalize_email(email):
    return (email or "").strip().lower()


def generate_internal_username():
    return f"u_{uuid.uuid4().hex}"


def display_user(user):
    if not user:
        return ""

    full_name = user.get_full_name().strip()

    if full_name and user.email:
        return f"{full_name} <{user.email}>"

    return full_name or user.email or "Benutzer ohne E-Mail"

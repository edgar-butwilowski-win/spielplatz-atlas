# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Inspection
from .planning import update_planning_after_completed_inspection


@receiver(post_save, sender=Inspection)
def update_planning_when_inspection_is_completed(sender, instance, **kwargs):
    if instance.status != Inspection.STATUS_COMPLETED:
        return

    transaction.on_commit(
        lambda: update_planning_after_completed_inspection(instance)
    )

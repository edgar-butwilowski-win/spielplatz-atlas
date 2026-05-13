# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

import json

from django.conf import settings
from django.utils import timezone

from .models import DefectAssignment, PushSubscription, SystemNotification


def assign_defect(defect, assigned_to, assigned_by=None):
    playground = defect.playground

    if not playground:
        return None, None

    assignment, _ = DefectAssignment.objects.update_or_create(
        defect=defect,
        defaults={
            "organization": playground.organization,
            "assigned_to": assigned_to,
            "assigned_by": assigned_by,
            "assigned_at": timezone.now(),
        },
    )

    notification = None

    if assigned_to:
        notification = create_defect_assignment_notification(
            defect=defect,
            recipient=assigned_to,
            created_by=assigned_by,
        )

    return assignment, notification


def create_defect_assignment_notification(defect, recipient, created_by=None):
    playground = defect.playground

    if not playground:
        return None

    target = ""
    if defect.equipment:
        target = f" am Spielgerät «{defect.equipment.name}»"
    elif defect.surface:
        target = f" bei «{defect.surface.name}»"
    elif defect.accessory:
        target = f" bei «{defect.accessory.name}»"

    title = "Neuer Mangel zugewiesen"
    message = f"{playground.name}: Mangel{target}. Bitte prüfen und Instandsetzung planen."

    notification = SystemNotification.objects.create(
        organization=playground.organization,
        recipient=recipient,
        created_by=created_by,
        title=title,
        message=message,
        notification_type=SystemNotification.TYPE_DEFECT_ASSIGNED,
        related_defect=defect,
        url=SystemNotification.build_defect_url(defect),
    )

    send_push_for_notification(notification)
    return notification


def send_push_for_notification(notification):
    subscriptions = PushSubscription.objects.filter(
        user=notification.recipient,
        organization=notification.organization,
        is_active=True,
    )

    if not subscriptions.exists():
        notification.delivery_status = SystemNotification.STATUS_NO_SUBSCRIPTION
        notification.delivery_error = "Für diese Person ist kein aktives Push-Gerät registriert."
        notification.save(update_fields=["delivery_status", "delivery_error", "updated_at"])
        return False

    vapid_private_key = getattr(settings, "WEBPUSH_VAPID_PRIVATE_KEY", "")
    vapid_email = getattr(settings, "WEBPUSH_VAPID_EMAIL", "")

    if not vapid_private_key or not vapid_email:
        notification.delivery_status = SystemNotification.STATUS_FAILED
        notification.delivery_error = "Web-Push ist nicht konfiguriert."
        notification.save(update_fields=["delivery_status", "delivery_error", "updated_at"])
        return False

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        notification.delivery_status = SystemNotification.STATUS_FAILED
        notification.delivery_error = "pywebpush ist nicht installiert."
        notification.save(update_fields=["delivery_status", "delivery_error", "updated_at"])
        return False

    payload = json.dumps(
        {
            "title": notification.title,
            "message": notification.message,
            "url": notification.url or "/internal/notifications/",
            "notification_id": notification.id,
        }
    )

    sent_any = False
    errors = []

    for subscription in subscriptions:
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh_key,
                "auth": subscription.auth_key,
            },
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims={"sub": f"mailto:{vapid_email}"},
            )
            sent_any = True
        except WebPushException as error:
            errors.append(str(error))

            response = getattr(error, "response", None)
            if response is not None and getattr(response, "status_code", None) in {404, 410}:
                subscription.is_active = False
                subscription.save(update_fields=["is_active", "last_seen_at"])
        except Exception as error:  # bewusst breit: Push darf Fachprozess nicht abbrechen
            errors.append(str(error))

    if sent_any:
        notification.delivery_status = SystemNotification.STATUS_SENT
        notification.sent_at = timezone.now()
        notification.delivery_error = "\n".join(errors)
        notification.save(update_fields=["delivery_status", "sent_at", "delivery_error", "updated_at"])
        return True

    notification.delivery_status = SystemNotification.STATUS_FAILED
    notification.delivery_error = "\n".join(errors) or "Push konnte nicht zugestellt werden."
    notification.save(update_fields=["delivery_status", "delivery_error", "updated_at"])
    return False

# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from accounts.admin_utils import get_user_organization

from .models import PushSubscription, SystemNotification


@login_required
def notification_list(request):
    organization = get_user_organization(request.user)

    if not request.user.is_superuser and not organization:
        messages.error(request, "Für Ihr Benutzerkonto ist keine aktive Organisation hinterlegt.")
        return redirect("public:index")

    notifications = SystemNotification.objects.filter(
        recipient=request.user,
    ).select_related("organization", "related_defect")

    if not request.user.is_superuser:
        notifications = notifications.filter(organization=organization)

    return render(
        request,
        "notifications/notification_list.html",
        {
            "notifications": notifications[:100],
            "webpush_public_key": getattr(settings, "WEBPUSH_VAPID_PUBLIC_KEY", ""),
            "push_enabled": bool(getattr(settings, "WEBPUSH_VAPID_PUBLIC_KEY", "")),
        },
    )


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        SystemNotification.objects.filter(recipient=request.user),
        id=notification_id,
    )
    notification.mark_as_read()

    if notification.url:
        return redirect(notification.url)

    return redirect("notifications:list")


@login_required
@ensure_csrf_cookie
def service_worker(request):
    response = render(
        request,
        "notifications/service-worker.js",
        content_type="application/javascript",
    )
    response["Service-Worker-Allowed"] = "/"
    return response


@login_required
@require_POST
def save_push_subscription(request):
    organization = get_user_organization(request.user)

    if not organization:
        return JsonResponse({"ok": False, "error": "Keine Organisation gefunden."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Ungültige Anfrage."}, status=400)

    endpoint = payload.get("endpoint")
    keys = payload.get("keys") or {}
    p256dh_key = keys.get("p256dh")
    auth_key = keys.get("auth")

    if not endpoint or not p256dh_key or not auth_key:
        return JsonResponse({"ok": False, "error": "Unvollständige Push-Daten."}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "organization": organization,
            "p256dh_key": p256dh_key,
            "auth_key": auth_key,
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "is_active": True,
        },
    )

    return JsonResponse({"ok": True})

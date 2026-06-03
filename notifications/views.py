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
from inspections.models import Defect
from internal.permissions import require_org_admin_permission

from .forms import DefectAssignmentForm
from .models import PushSubscription, SystemNotification
from .services import assign_defect


@login_required
@ensure_csrf_cookie
def notification_list(request):
    organization = get_user_organization(request.user)

    if not request.user.is_superuser and not organization:
        messages.error(request, "Für Ihr Benutzerkonto ist keine aktive Organisation hinterlegt.")
        return redirect("public:index")

    notifications = SystemNotification.objects.filter(
        recipient=request.user,
    ).select_related("organization", "related_defect")

    active_push_subscriptions_count = 0

    if not request.user.is_superuser:
        notifications = notifications.filter(organization=organization)
        active_push_subscriptions_count = PushSubscription.objects.filter(
            user=request.user,
            organization=organization,
            is_active=True,
        ).count()
    else:
        active_push_subscriptions_count = PushSubscription.objects.filter(
            user=request.user,
            is_active=True,
        ).count()

    return render(
        request,
        "notifications/notification_list.html",
        {
            "notifications": notifications[:100],
            "webpush_public_key": getattr(settings, "WEBPUSH_VAPID_PUBLIC_KEY", ""),
            "push_enabled": bool(getattr(settings, "WEBPUSH_VAPID_PUBLIC_KEY", "")),
            "active_push_subscriptions_count": active_push_subscriptions_count,
        },
    )


@login_required
@require_POST
def assign_defect_view(request, defect_id):
    defect = get_object_or_404(
        Defect.objects.select_related(
            "playground",
            "playground__organization",
            "equipment",
            "surface",
            "accessory",
            "assignment",
            "assignment__assigned_to",
        ),
        id=defect_id,
    )

    if not defect.playground:
        messages.error(request, "Dieser Mangel ist keinem Spielplatz zugeordnet.")
        return redirect("public:index")

    organization = defect.playground.organization
    require_org_admin_permission(request.user, organization)

    form = DefectAssignmentForm(
        request.POST,
        organization=organization,
        current_user=request.user,
    )

    if form.is_valid():
        assigned_to = form.cleaned_data["assigned_to"]
        if not assigned_to and defect.status == Defect.STATUS_PLANNED:
            messages.error(request, "Die Zuweisung kann nicht entfernt werden, solange der Mangel den Status «Geplant» hat.")
            return redirect("internal:edit_defect", defect_id=defect.id)

        _, notification = assign_defect(
            defect=defect,
            assigned_to=assigned_to,
            assigned_by=request.user,
        )

        if assigned_to:
            if notification and notification.delivery_status == SystemNotification.STATUS_SENT:
                messages.success(request, "Der Mangel wurde zugewiesen. Die Push-Meldung wurde gesendet.")
            elif notification and notification.delivery_status == SystemNotification.STATUS_NO_SUBSCRIPTION:
                messages.info(request, "Der Mangel wurde zugewiesen. Die Person hat noch kein Push-Gerät registriert.")
            else:
                messages.info(request, "Der Mangel wurde zugewiesen. Die Systemnachricht wurde gespeichert.")
        else:
            messages.success(request, "Die Zuweisung wurde entfernt.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect("internal:edit_defect", defect_id=defect.id)


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

    subscription, _ = PushSubscription.objects.update_or_create(
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

    active_count = PushSubscription.objects.filter(
        user=request.user,
        organization=organization,
        is_active=True,
    ).count()

    return JsonResponse({"ok": True, "subscription_id": subscription.id, "active_count": active_count})

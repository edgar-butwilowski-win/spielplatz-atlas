# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("notifications/", views.notification_list, name="list"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_read"),
    path("push-subscriptions/save/", views.save_push_subscription, name="save_push_subscription"),
    path("service-worker.js", views.service_worker, name="service_worker"),
]

# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.urls import path

from . import views

app_name = "internal"

urlpatterns = [
    path(
        "playgrounds/<slug:organization_slug>/<slug:playground_slug>/inspections/new/",
        views.create_inspection,
        name="create_inspection",
    ),
    path(
        "playgrounds/<slug:organization_slug>/<slug:playground_slug>/defects/new/",
        views.create_defect,
        name="create_defect",
    ),
    path(
        "inspection-answers/<int:answer_id>/defects/new/",
        views.create_defect_from_inspection_answer,
        name="create_defect_from_inspection_answer",
    ),
    path(
        "inspections/<int:inspection_id>/",
        views.inspection_detail,
        name="inspection_detail",
    ),
    path(
        "inspections/<int:inspection_id>/answers/save/",
        views.save_inspection_answers,
        name="save_inspection_answers",
    ),
    path(
        "inspections/<int:inspection_id>/complete/",
        views.complete_inspection,
        name="complete_inspection",
    ),
]

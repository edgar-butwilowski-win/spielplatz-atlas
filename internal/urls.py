# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.urls import path

from . import control_status, dashboard, defect_management, export_views, planning_views, views, work_order_views

app_name = "internal"

urlpatterns = [
    path("dashboard/", dashboard.dashboard, name="dashboard"),
    path("control-status/", control_status.control_status, name="control_status"),
    path("defects/", defect_management.defect_management, name="defect_management"),
    path("defects/<int:defect_id>/assign/", defect_management.update_defect_assignment, name="update_defect_assignment"),
    path("defects/<int:defect_id>/planning/", defect_management.update_defect_planning, name="update_defect_planning"),
    path("defects/<int:defect_id>/status/", defect_management.update_defect_status, name="update_defect_status"),
    path("work-orders/", work_order_views.work_orders, name="work_orders"),
    path("work-orders/<int:order_id>/save/", work_order_views.update_work_order, name="update_work_order"),
    path("my-inspections/", planning_views.my_inspections, name="my_inspections"),
    path("inspection-planning/", planning_views.inspection_planning, name="inspection_planning"),
    path("inspection-planning/rebuild/", planning_views.rebuild_inspection_planning, name="rebuild_inspection_planning"),
    path("inspection-tasks/<int:task_id>/save/", planning_views.update_inspection_task, name="update_inspection_task"),
    path("inspection-tasks/<int:task_id>/cancel/", planning_views.cancel_inspection_task, name="cancel_inspection_task"),
    path("inspection-tasks/<int:task_id>/suspend/", planning_views.suspend_inspection_task, name="suspend_inspection_task"),
    path("inspection-tasks/<int:task_id>/accept/", planning_views.accept_inspection_task, name="accept_inspection_task"),
    path("inspection-tasks/<int:task_id>/start/", planning_views.start_inspection_from_task, name="start_inspection_from_task"),
    path("equipment/<int:equipment_id>/renovation/save/", views.update_equipment_renovation, name="update_equipment_renovation"),
    path("equipment/<int:equipment_id>/abort/", views.abort_equipment, name="abort_equipment"),
    path("playgrounds/<slug:organization_slug>/<slug:playground_slug>/inspections/new/", views.create_inspection, name="create_inspection"),
    path("playgrounds/<slug:organization_slug>/<slug:playground_slug>/defects/new/", views.create_defect, name="create_defect"),
    path("defects/<int:defect_id>/edit/", defect_management.edit_defect, name="edit_defect"),
    path("defects/<int:defect_id>/pdf/", export_views.defect_pdf, name="defect_pdf"),
    path("inspection-answers/<int:answer_id>/defects/new/", views.create_defect_from_inspection_answer, name="create_defect_from_inspection_answer"),
    path("inspections/<int:inspection_id>/", views.inspection_detail, name="inspection_detail"),
    path("inspections/<int:inspection_id>/pdf/", export_views.inspection_pdf, name="inspection_pdf"),
    path("inspections/<int:inspection_id>/answers/save/", views.save_inspection_answers, name="save_inspection_answers"),
    path("inspections/<int:inspection_id>/complete/", views.complete_inspection, name="complete_inspection"),
]

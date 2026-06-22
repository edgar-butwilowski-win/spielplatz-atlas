from django.db import models, transaction
from django.utils import timezone


def cancel_related_items_for_aborted_equipment(equipment):
    """Cancel open follow-up objects after a play equipment item has been aborted."""
    from inspections.models import Defect, MaintenanceAction
    from inspections.work_orders import WorkOrder

    now = timezone.now()
    today = timezone.localdate()

    open_defect_statuses = [Defect.STATUS_OPEN, Defect.STATUS_PLANNED]
    active_maintenance_statuses = [MaintenanceAction.STATUS_PLANNED, MaintenanceAction.STATUS_IN_PROGRESS]
    active_work_order_statuses = [
        WorkOrder.STATUS_OPEN,
        WorkOrder.STATUS_PLANNED,
        WorkOrder.STATUS_IN_PROGRESS,
    ]

    defects = Defect.objects.filter(equipment=equipment)
    canceled_defects = defects.filter(status__in=open_defect_statuses).update(
        status=Defect.STATUS_CANCELED,
        updated_at=now,
    )

    canceled_maintenance_actions = MaintenanceAction.objects.filter(
        defect__equipment=equipment,
        status__in=active_maintenance_statuses,
    ).update(
        status=MaintenanceAction.STATUS_CANCELLED,
        completed_date=today,
        updated_at=now,
    )

    work_order_ids = list(
        WorkOrder.objects.filter(
            order_type__in=[WorkOrder.TYPE_DEFECT_REPAIR, WorkOrder.TYPE_RENOVATION],
            status__in=active_work_order_statuses,
        )
        .filter(
            models.Q(equipment=equipment)
            | models.Q(defect__equipment=equipment)
            | models.Q(maintenance_action__defect__equipment=equipment)
        )
        .values_list("id", flat=True)
        .distinct()
    )
    canceled_work_orders = WorkOrder.objects.filter(id__in=work_order_ids).update(
        status=WorkOrder.STATUS_CANCELLED,
        updated_at=now,
    )

    return {
        "defects": canceled_defects,
        "maintenance_actions": canceled_maintenance_actions,
        "work_orders": canceled_work_orders,
    }


@transaction.atomic
def abort_play_equipment(equipment, *, demolition_date=None):
    """Abort a play equipment item and cancel its active follow-up objects."""
    demolition_date = demolition_date or timezone.localdate()

    equipment.demolition_date = demolition_date
    equipment.is_active = False
    equipment.save(update_fields=["demolition_date", "is_active"], skip_abort_cleanup=True)

    return cancel_related_items_for_aborted_equipment(equipment)

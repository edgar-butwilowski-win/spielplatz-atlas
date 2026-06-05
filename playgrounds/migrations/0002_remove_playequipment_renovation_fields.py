from datetime import date

from django.db import migrations


ACTIVE_RENOVATION_STATUSES = ["open", "planned", "in_progress", "suspended"]


def suggested_credit_name(year):
    return "Sammelkredit Sanierungen %s" % year if year else "Sammelkredit Sanierungen"


def renovation_due_date(year):
    if not year:
        return None
    return date(year, 12, 31)


def migrate_equipment_renovations_to_work_orders(apps, schema_editor):
    PlayEquipment = apps.get_model("playgrounds", "PlayEquipment")
    WorkOrder = apps.get_model("inspections", "WorkOrder")

    equipment_queryset = PlayEquipment.objects.select_related(
        "playground",
        "playground__organization",
    ).filter(recommended_renovation_year__isnull=False)

    for equipment in equipment_queryset:
        year = equipment.recommended_renovation_year
        work_order = WorkOrder.objects.filter(
            equipment=equipment,
            order_type="renovation",
            status__in=ACTIVE_RENOVATION_STATUSES,
        ).order_by("created_at").first()

        title = "Sanierung %s" % equipment.name
        description = equipment.renovation_comment or "Sanierung gemaess Spielgeraeteplanung."
        due_date = renovation_due_date(year)

        if work_order is None:
            WorkOrder.objects.create(
                equipment=equipment,
                organization=equipment.playground.organization,
                playground=equipment.playground,
                title=title,
                description=description,
                order_type="renovation",
                status="open",
                priority="normal",
                source="equipment_renovation",
                renovation_type=equipment.renovation_type or "",
                renovation_year=year,
                due_date=due_date,
                credit_name=suggested_credit_name(year),
                public_visible=False,
            )
            continue

        changed = False
        updates = {
            "organization": equipment.playground.organization,
            "playground": equipment.playground,
            "title": title,
            "description": description,
            "source": "equipment_renovation",
            "renovation_type": equipment.renovation_type or work_order.renovation_type,
            "renovation_year": year,
            "due_date": due_date,
        }
        if not work_order.credit_name:
            updates["credit_name"] = suggested_credit_name(year)
        for field_name, value in updates.items():
            if getattr(work_order, field_name) != value:
                setattr(work_order, field_name, value)
                changed = True
        if changed:
            work_order.save()


class Migration(migrations.Migration):

    dependencies = [
        ("playgrounds", "0001_initial"),
        ("inspections", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_equipment_renovations_to_work_orders, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="playequipment",
            name="renovation_type",
        ),
        migrations.RemoveField(
            model_name="playequipment",
            name="recommended_renovation_year",
        ),
        migrations.RemoveField(
            model_name="playequipment",
            name="renovation_comment",
        ),
    ]

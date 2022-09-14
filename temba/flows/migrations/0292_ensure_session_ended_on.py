# Generated by Django 4.0.6 on 2022-07-12 09:37

from django.db import migrations
from django.utils import timezone


def ensure_session_ended_on(apps, schema_editor):
    FlowSession = apps.get_model("flows", "FlowSession")

    num_updated = 0
    while True:
        batch = list(FlowSession.objects.filter(ended_on=None).exclude(status="W").only("id", "ended_on")[:100])
        if not batch:
            break

        FlowSession.objects.filter(id__in=[r.id for r in batch]).update(ended_on=timezone.now())

        num_updated += len(batch)
        print(f"Updated {num_updated} non-waiting sessions without an ended_on")


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("flows", "0291_flowrun_flows_run_active_or_waiting_has_session"),
    ]

    operations = [migrations.RunPython(ensure_session_ended_on, reverse)]

# Generated by Django 4.0.7 on 2022-10-06 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0169_alter_contact_language_alter_contact_name"),
        ("msgs", "0191_alter_exportmessagestask_end_date_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="exportmessagestask",
            name="with_fields",
            field=models.ManyToManyField(related_name="%(class)s_exports", to="contacts.contactfield"),
        ),
    ]

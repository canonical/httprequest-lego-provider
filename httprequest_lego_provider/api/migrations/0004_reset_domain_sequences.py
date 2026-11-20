# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Repair sequences after copying records from the original app's tables."""

from django.core.management.color import no_style
from django.db import migrations


def reset_sequences(apps, schema_editor):
    """Advance the domain and permission sequences past their existing IDs.

    Args:
        apps: Historical application registry.
        schema_editor: Schema editor for the database being migrated.
    """
    models = [
        apps.get_model("api", "Domain"),
        apps.get_model("api", "DomainUserPermission"),
    ]
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        for statement in connection.ops.sequence_reset_sql(no_style(), models):
            cursor.execute(statement)


class Migration(migrations.Migration):
    """Repair ID generation for new and already-upgraded deployments."""

    dependencies = [
        ("api", "0003_add_access_level_and_more"),
    ]

    operations = [
        migrations.RunPython(reset_sequences, migrations.RunPython.noop),
    ]

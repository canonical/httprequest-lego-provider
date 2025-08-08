# Migrate the "httprequest_lego_provider_domain" table to the "api_domain" table
# and the "httprequest_lego_provider_domainuserpermission" table to the "api_domainuserpermission" table.
# This accommodates the rename of the Django app from "httprequest_lego_provider" to "api" as implemented in
# https://github.com/canonical/httprequest-lego-provider/pull/97

from django.db import migrations


def forwards(apps, schema_editor):
    conn = schema_editor.connection
    existing_tables = conn.introspection.table_names()
    with conn.cursor() as cursor:
        if "httprequest_lego_provider_domain" in existing_tables:
            cursor.execute(
                """
                INSERT INTO api_domain
                SELECT *
                FROM httprequest_lego_provider_domain;
            """
            )
            cursor.execute(
                """
                INSERT INTO api_domainuserpermission
                SELECT *
                FROM httprequest_lego_provider_domainuserpermission;
            """
            )
            cursor.execute(
                """
                DROP TABLE httprequest_lego_provider_domainuserpermission;
            """
            )
            cursor.execute(
                """
                DROP TABLE httprequest_lego_provider_domain;
            """
            )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]

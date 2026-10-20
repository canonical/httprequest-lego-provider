# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Regression tests for database migrations."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("existing_ids", [[], [1, 39, 73]])
def test_reset_domain_sequences(existing_ids):
    """
    arrange: copy explicit IDs without advancing sequences, as the app rename did.
    act: apply the sequence repair migration.
    assert: existing records survive and new records receive unused IDs.
    """
    if connection.vendor != "postgresql":
        pytest.skip("Stale ID sequences require PostgreSQL; set POSTGRESQL_DB_CONNECT_STRING.")

    previous = [("api", "0003_add_access_level_and_more")]
    target = [("api", "0004_reset_domain_sequences")]
    executor = MigrationExecutor(connection)
    executor.migrate(previous)
    old_apps = executor.loader.project_state(previous).apps
    domain_model = old_apps.get_model("api", "Domain")
    permission_model = old_apps.get_model("api", "DomainUserPermission")
    user_model = old_apps.get_model("auth", "User")
    try:
        user = user_model.objects.create(username="migration-user")
        for record_id in existing_ids:
            domain = domain_model.objects.create(id=record_id, fqdn=f"domain{record_id}.com")
            permission_model.objects.create(
                id=record_id,
                domain=domain,
                user=user,
                access_level="domain",
                text=f"permission {record_id}",
            )

        executor = MigrationExecutor(connection)
        executor.migrate(target)
        apps = executor.loader.project_state(target).apps
        domain_model = apps.get_model("api", "Domain")
        permission_model = apps.get_model("api", "DomainUserPermission")

        assert list(domain_model.objects.order_by("id").values_list("id", "fqdn")) == [
            (record_id, f"domain{record_id}.com") for record_id in existing_ids
        ]
        assert list(
            permission_model.objects.order_by("id").values_list(
                "id", "domain_id", "user_id", "access_level", "text"
            )
        ) == [
            (record_id, record_id, user.pk, "domain", f"permission {record_id}")
            for record_id in existing_ids
        ]
        for index in range(2):
            domain = domain_model.objects.create(fqdn=f"new{index}.com")
            permission = permission_model.objects.create(
                domain=domain, user_id=user.pk, access_level="domain"
            )
            assert domain.pk > max(existing_ids, default=0)
            assert permission.pk > max(existing_ids, default=0)
    finally:
        MigrationExecutor(connection).migrate(target)

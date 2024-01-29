# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Serializers."""

from rest_framework import serializers

from .models import Domain, DomainUserPermission


class DomainSerializer(serializers.ModelSerializer):
    """Serializer for the Domain objects."""

    class Meta:
        """Serializer configuration.

        Attributes:
            model: the model to serialize.
            fields: fields to serialize.
        """

        model = Domain
        fields = "__all__"


class DomainUserPermissionSerializer(serializers.ModelSerializer):
    """Serializer for the DomainUserPermission objects."""

    class Meta:
        """Serializer configuration.

        Attributes:
            model: the model to serialize.
            fields: fields to serialize.
        """

        model = DomainUserPermission
        fields = "__all__"

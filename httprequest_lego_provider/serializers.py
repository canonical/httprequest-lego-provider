# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Serializers."""

from django.contrib.auth.hashers import make_password

# imported-auth-user has to be disabled as the import is needed for UserSerializer
# pylint:disable=imported-auth-user
from django.contrib.auth.models import User
from rest_framework import serializers

from .forms import FQDN_PREFIX
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

    def create(self, validated_data):
        """Override default ModelSerializer create call to add the FQDN prefix.

        Arguments:
            validated_data: Serializer validated data

        Returns:
            The created Domain object.
        """
        validated_data["fqdn"] = f"{FQDN_PREFIX}{validated_data['fqdn']}"
        return super().create(validated_data)


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


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User objects."""

    class Meta:
        """Serializer configuration.

        Attributes:
            model: the model to serialize.
            fields: fields to serialize.
            extra_kwargs: extra per-field parameters.
        """

        model = User
        fields = ["url", "username", "email", "groups", "password"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        """Override default ModelSerializer create call to hash the password.

        Arguments:
            validated_data: Serializer validated data

        Returns:
            The created User object.
        """
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)

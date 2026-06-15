from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from core.enums import Roles
from users.helper.auth_tokens import (
    blacklist_all_refresh_tokens_for_user,
    revoke_access_token,
)

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "confirm_password",
            "tenant",
        )
        extra_kwargs = {
            "username": {"validators": []},
            "email": {"validators": []},
            "tenant": {"required": False},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs

    def validate_username(self, value):
        user = User.all_objects.filter(username=value).first()
        if user:
            raise serializers.ValidationError("Username already exists.", code="unique")
        return value

    def validate_email(self, value):
        value = value.lower()
        user = User.all_objects.filter(email=value).first()
        if user and user.is_verified:
            raise serializers.ValidationError("Email already exists.", code="unique")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        creator = request.user
        email = validated_data["email"].lower()

        validated_data.pop("confirm_password")

        existing_user = User.all_objects.filter(email=email).first()
        if existing_user and existing_user.is_verified:
            raise serializers.ValidationError({"email": "Email already exists."})

        if creator.role == Roles.SUPER_ADMIN:
            tenant = validated_data.get("tenant")
            if not tenant:
                raise serializers.ValidationError({"tenant": "Tenant is required."})
            role = Roles.ADMIN
        elif creator.role == Roles.ADMIN:
            tenant = creator.tenant
            role = Roles.GAMER
        else:
            raise PermissionDenied("You cannot create users.")

        if existing_user:
            for field, value in validated_data.items():
                if field not in ["password", "role", "tenant"]:
                    setattr(existing_user, field, value)
            existing_user.role = role
            existing_user.tenant = tenant
            existing_user.set_password(validated_data["password"])
            existing_user.save()
            return existing_user

        validated_data["role"] = role
        validated_data["tenant"] = tenant
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for administrative user state management.

    Allows admins to enable, disable, or restore users.
    All identity and profile fields are read-only.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_verified",
            "is_active",
            "deleted_at",
            "created_at",
            "updated_at",
            "tenant",
        )
        read_only_fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_verified",
            "created_at",
            "updated_at",
            "tenant",
        )


class SelfUserSerializer(serializers.ModelSerializer):
    """
    Serializer for self-service user profile operations.

    Used by authenticated users to view and update their own profile.
    Identity and audit fields are read-only and cannot be modified
    through this serializer.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "created_at",
        )
        read_only_fields = ("id", "username", "email", "created_at")


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing the authenticated user's password.

    Requires the current password for verification and validates the
    new password using Django's configured password validators.
    """

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def save(self, **kwargs):
        request = self.context["request"]
        user = request.user

        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])

        revoke_access_token(request.auth)
        blacklist_all_refresh_tokens_for_user(user)

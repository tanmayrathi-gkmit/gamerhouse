from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.enums import Roles, TenantStatus
from tenants.models import Tenant
from users.helper.auth_tokens import blacklist_refresh_token, revoke_access_token

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new user.

    Responsibilities:
    - Validate password strength
    - Ensure password and confirm_password match
    - Enforce username and email uniqueness
    - Create user via UserManager
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "confirm_password",
        )
        extra_kwargs = {
            "username": {"validators": []},
            "email": {"validators": []},
        }

    def validate(self, attrs):
        tenant_id = self.context.get("tenant_id")
        try:
            Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            raise serializers.ValidationError(
                {"tenant": "Invalid tenant_id. Tenant does not exist."}
            )
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs

    def validate_username(self, value):
        """
        Reject registration if the username already exists.
        """
        user = User.all_objects.filter(username=value).first()

        if user:
            raise serializers.ValidationError(
                "Username already exists.",
                code="unique",
            )

        return value

    def validate_email(self, value):
        """
        Reject registration if the email already exists.
        """
        value = value.lower()
        user = User.all_objects.filter(email=value).first()

        if user and user.is_verified:
            raise serializers.ValidationError(
                "Email already exists.",
                code="unique",
            )

        return value

    def create(self, validated_data):
        """
        Create user using the UserManager to ensure
        proper password hashing and defaults.
        """
        tenant_id = self.context["tenant_id"]
        validated_data.pop("confirm_password")
        email = validated_data["email"].lower()

        existing_user = User.all_objects.filter(email=email).first()

        role = Roles.GAMER
        validated_data["tenant_id"] = tenant_id
        if existing_user:
            for field, value in validated_data.items():
                if field not in ["password"]:
                    setattr(existing_user, field, value)
            existing_user.set_password(validated_data["password"])
            existing_user.role = role
            existing_user.save()
            return existing_user
        return User.objects.create_user(**validated_data)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that injects user roles
    into the issued access and refresh tokens.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token


class LoginSerializer(serializers.Serializer):
    """
    Validate credentials and return JWT access and refresh tokens.
    """

    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password")
        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_verified:
            raise serializers.ValidationError("User not verified.")
        if not user.is_active or user.deleted_at is not None:
            raise serializers.ValidationError("Account is inactive.")
        if user.role != Roles.SUPER_ADMIN:
            if not user.tenant:
                raise serializers.ValidationError(
                    "User is not associated with any tenant."
                )
            if user.tenant.status == TenantStatus.INACTIVE:
                raise serializers.ValidationError(
                    "Tenant is not active. Please contact support."
                )
        return attrs


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for refresh-token based logout (blacklisting).
    """

    refresh = serializers.CharField()

    @transaction.atomic
    def save(self, **kwargs):
        request = self.context.get("request")
        revoke_access_token(request.auth)

        try:
            blacklist_refresh_token(self.validated_data["refresh"])
        except TokenError:
            raise serializers.ValidationError({"refresh": "Invalid or expired token"})


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")
        return attrs

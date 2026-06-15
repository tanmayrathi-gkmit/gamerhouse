import hashlib
import hmac
import secrets
import string

from django.conf import settings


def _generate_token(email: str) -> str:
    raw = f"{email}{secrets.token_urlsafe(32)}{settings.SECRET_KEY}"
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_email_verification_token(email: str) -> str:
    return _generate_token(email)


def generate_password_reset_token(email: str) -> str:
    return _generate_token(email)


def generate_otp(length=6):
    return "".join(secrets.choice(string.digits) for _ in range(length))


def generate_otp_hash(otp):
    """Hash OTP using SHA-256 for secure storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp_hash(otp: str, hashed_otp: str) -> bool:
    """
    Verify if the given OTP matches the hashed OTP.
    Uses hmac.compare_digest to prevent timing attacks.
    """
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    return hmac.compare_digest(otp_hash, hashed_otp)

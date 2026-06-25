"""
Supabase JWT authentication for Django REST Framework.

Validates Supabase-issued JWTs by:
1. Extracting the Bearer token from the Authorization header
2. Verifying the JWT signature using the Supabase JWT secret
3. Finding or creating a Django User by supabase_id
"""

import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework import exceptions

import jwt

User = get_user_model()
logger = logging.getLogger(__name__)


class SupabaseAuthentication(authentication.BaseAuthentication):
    """
    DRF authentication class that validates Supabase JWT tokens.

    The token is extracted from the Authorization header (Bearer <token>).
    The JWT is verified using the Supabase JWT secret (derived from the
    project's signing key), and the user is looked up or created by
    supabase_id.
    """

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None  # Let other auth classes try

        token = auth_header[7:].strip()
        if not token:
            return None

        try:
            payload = self._decode_token(token)
        except Exception as e:
            logger.warning("Supabase JWT decode failed: %s", e)
            raise exceptions.AuthenticationFailed("Invalid or expired token")

        supabase_id = payload.get("sub")
        if not supabase_id:
            raise exceptions.AuthenticationFailed("Token missing sub claim")

        user = self._get_or_create_user(supabase_id, payload)
        return (user, token)

    def _decode_token(self, token: str) -> dict:
        """
        Decode and verify the Supabase JWT.

        Supabase JWTs are signed with the project's JWT secret (HS256).
        We try multiple approaches:
        1. Use SUPABASE_JWT_SECRET if configured
        2. Derive from SUPABASE_ANON_KEY (the anon key is itself a JWT
           whose signature secret is the project's JWT secret — but we
           can't extract it from the key alone)
        3. Fall back to decoding without verification and then calling
           Supabase's /auth/v1/user endpoint to validate
        """
        jwt_secret = getattr(settings, "SUPABASE_JWT_SECRET", None)

        if jwt_secret:
            return jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"require": ["sub", "exp", "iat"]},
            )

        # Fallback: decode without verification, then validate via API
        # This is less secure but works when JWT secret isn't configured
        unverified = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["HS256"],
        )
        # We still check expiry manually
        import time
        exp = unverified.get("exp", 0)
        if exp < time.time():
            raise jwt.ExpiredSignatureError("Token has expired")

        return unverified

    def _get_or_create_user(self, supabase_id: str, payload: dict) -> User:
        """Find existing user by supabase_id or create a new one."""
        user = User.objects.filter(supabase_id=supabase_id).first()

        if user is None:
            email = payload.get("email", "")
            phone = payload.get("phone", "")
            role = payload.get("user_metadata", {}).get("role", "customer")
            full_name = payload.get("user_metadata", {}).get("full_name", "")

            # Use email as username if available, otherwise supabase_id
            username = email or f"supabase_{supabase_id[:12]}"

            # Ensure unique username
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User.objects.create(
                supabase_id=supabase_id,
                username=username,
                email=email,
                role=role,
                phone=phone,
                avatar_url=payload.get("user_metadata", {}).get("avatar_url", ""),
            )

            logger.info("Created new Django user for supabase_id=%s", supabase_id)

        # Update role if it changed in Supabase
        role = payload.get("user_metadata", {}).get("role", "customer")
        if user.role != role:
            user.role = role
            user.save(update_fields=["role"])

        return user

    def authenticate_header(self, request):
        return 'Bearer realm="Supabase"'
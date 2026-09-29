from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed
from .models import Applicant


def issue_applicant_token(applicant):
    """Manually build a JWT for an Applicant, since Applicant is not the AUTH_USER_MODEL."""
    token = RefreshToken()
    token["applicant_id"] = applicant.id
    token["role"] = "applicant"
    return {
        "refresh": str(token),
        "access": str(token.access_token),
    }


class ApplicantJWTAuthentication(JWTAuthentication):
    """
    Strictly authenticates applicant tokens only - rejects staff tokens.
    Used on applicant-only endpoints where we want a hard guarantee.
    """

    def get_user(self, validated_token):
        if validated_token.get("role") != "applicant":
            raise AuthenticationFailed("Not an applicant token")
        applicant_id = validated_token.get("applicant_id")
        try:
            applicant = Applicant.objects.get(id=applicant_id)
        except Applicant.DoesNotExist:
            raise AuthenticationFailed("Applicant not found")
        applicant.is_authenticated = True
        applicant.is_applicant = True
        return applicant


class CombinedJWTAuthentication(JWTAuthentication):
    """
    Global default authenticator. Understands BOTH staff (Django User) tokens
    and applicant tokens.

    Without this, an applicant's token hitting any endpoint that doesn't
    explicitly use ApplicantJWTAuthentication (e.g. the public job list)
    would fail authentication entirely - because the standard JWTAuthentication
    expects a "user_id" claim that applicant tokens don't have - and DRF
    returns 401 before permission_classes (like AllowAny) even get checked.
    """

    def get_user(self, validated_token):
        if validated_token.get("role") == "applicant":
            applicant_id = validated_token.get("applicant_id")
            try:
                applicant = Applicant.objects.get(id=applicant_id)
            except Applicant.DoesNotExist:
                raise AuthenticationFailed("Applicant not found")
            applicant.is_authenticated = True
            applicant.is_applicant = True
            return applicant
        # Not an applicant token - fall back to standard Django User lookup (HR/Admin)
        return super().get_user(validated_token)

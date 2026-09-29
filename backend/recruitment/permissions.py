from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "role", None) == "admin")


class IsHR(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "role", None) == "hr")


class IsAdminOrHR(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "role", None) in ("admin", "hr"))


class IsApplicant(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "is_applicant", False))

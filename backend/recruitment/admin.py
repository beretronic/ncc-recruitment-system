from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Applicant, Job, Application, Interview, StatusAuditLog


class CustomUserAdmin(UserAdmin):
    """
    Uses Django's proper UserAdmin so passwords are hashed correctly when
    creating HR/Admin accounts from the admin panel, and adds the custom
    `role` field to the forms.
    """
    fieldsets = UserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")


admin.site.register(User, CustomUserAdmin)
admin.site.register(Applicant)
admin.site.register(Job)
admin.site.register(Application)
admin.site.register(Interview)
admin.site.register(StatusAuditLog)

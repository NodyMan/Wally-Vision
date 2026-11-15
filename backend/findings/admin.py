from django.contrib import admin

from .models import Finding


@admin.action(description="Mark selected findings as reviewed")
def mark_reviewed(modeladmin, request, queryset):
    queryset.update(status=Finding.STATUS_REVIEWED)


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ("id", "ra", "dec", "nickname", "status", "created_at")
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    search_fields = ("note", "nickname")
    readonly_fields = ("ip_hash", "created_at")
    actions = [mark_reviewed]

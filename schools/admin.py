from django.contrib import admin
from .models import School, SchoolNote, SchoolSensor


class SchoolSensorInline(admin.TabularInline):
    """A school's ranked sensor list, read only (assign_sensors builds it)."""
    model = SchoolSensor
    extra = 0
    can_delete = False
    readonly_fields = ('rank', 'sensor', 'distance_m')
    ordering = ('rank',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    inlines = [SchoolSensorInline]
@admin.register(SchoolNote)
class SchoolNoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'author', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'content', 'school__name')
    readonly_fields = ('created_at', 'updated_at')
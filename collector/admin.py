from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Host, Parameter


class HostAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip', 'community', 'port')
    filter_horizontal = ('parameters',)
    fieldsets = [
        (
            None,
            {
                'fields': ['name', 'ip', 'description', 'parameters']
            }
        ),
        (
            _('SNMP'),
            {
                'fields': ['community', 'port'],
                'classes': ['collapse']
            }
        ),
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('name',)
        return self.readonly_fields


class ParameterAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'oid', 'in_use')
    fieldsets = [
        (
            None,
            {
                'fields': ['name', 'type', 'description']
            }
        ),
        (
            _('SNMP'),
            {
                'fields': ['oid'],
                'classes': ['collapse']
            }
        )
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('name', 'type')
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False

    def in_use(self, obj: Parameter) -> bool:
        """
        Indicates if the parameter is enabled for at least one host.

        :param obj: parameter which usage is to be verified
        :return: parameter's state of usage
        """
        return obj.hosts.exists()
    in_use.boolean = True
    in_use.short_description = _('in use?')


admin.site.register(Host, HostAdmin)
admin.site.register(Parameter, ParameterAdmin)

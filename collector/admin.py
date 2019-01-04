from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Group, Host, Instance, Parameter, Tag, TagValue

restricted_names = ['host', 'instance']


# ------------------------------- ModelForms -------------------------------- #


class AlwaysValidForm(forms.ModelForm):
    """
    A workaround for inlines without change permission not returning
    all fields causing default ModelForm to complain. Data are unchanged
    so form might be assumed to be always valid.
    """

    def is_valid(self):
        return True

    class Meta:
        model = Parameter
        fields = '__all__'


class ParameterCollisionForm(forms.ModelForm):
    def clean(self):
        """
        Tags come from several sources: hostname, instance name,
        indexing parameters and tags themselves. Keeping names of
        them all unique prevents tags overriding.
        """
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        indexing = cleaned_data.get('indexing')

        if indexing:
            if name in restricted_names:
                message = _('Name \'%(name)s\' is restricted for '
                            'indexing parameter.')
                error = forms.ValidationError(
                    message=message,
                    code='invalid',
                    params={'name': name}
                )
                self.add_error('name', error)
                self.add_error('indexing', error)
            elif Tag.objects.filter(name=name).exists():
                message = _('Name \'%(name)s\' is restricted for indexing '
                            'parameter because it collides with the tag.')
                error = forms.ValidationError(
                    message=message,
                    code='invalid',
                    params={'name': name}
                )
                self.add_error('name', error)
                self.add_error('indexing', error)
        return cleaned_data

    class Meta:
        model = Parameter
        fields = '__all__'


class InstanceForm(forms.ModelForm):
    def clean_oid(self):
        """
        Replaces empty OID with default value. Instance of tabular
        parameter should have non-zero OID and instance of scalar
        parameter should have zero OID.
        """
        group = self.cleaned_data['group']
        oid = self.cleaned_data['oid']
        if oid is None:
            oid = self.instance._meta.get_field('oid').default

        if oid == 0 and group.type == Group.TABULAR:
            raise forms.ValidationError(
                message=_('Tabular parameters should have non-zero OID.'),
                code='invalid'
            )
        elif oid and group.type == Group.SCALAR:
            raise forms.ValidationError(
                message=_('Scalar parameters should have zero OID.'),
                code='invalid'
            )
        return oid

    def clean_name(self):
        """
        Instance of tabular parameter should be named and instance of
        scalar parameter shouldn't.
        """
        group = self.cleaned_data['group']
        name = self.cleaned_data['name']

        if not name and group.type == Group.TABULAR:
            raise forms.ValidationError(
                message=_('Tabular parameters require a name.'),
                code='invalid'
            )
        elif name and group.type == Group.SCALAR:
            raise forms.ValidationError(
                message=_('Scalar parameters does not require a name.'),
                code='invalid'
            )
        return name

    class Meta:
        model = Instance
        fields = '__all__'


class TagForm(forms.ModelForm):
    def clean_name(self):
        """
        Tags come from several sources: hostname, instance name,
        indexing parameters and tags themselves. Keeping names of
        them all unique prevents tags overriding.
        """
        name = self.cleaned_data['name']

        if name in restricted_names:
            raise forms.ValidationError(
                message=_('Name \'%(name)s\' is restricted.'),
                code='invalid',
                params={'name': name}
            )
        elif Parameter.objects.filter(name=name, indexing=True).exists():
            raise forms.ValidationError(
                message=_('Name \'%(name)s\' collides '
                          'with indexing parameter.'),
                code='invalid',
                params={'name': name}
            )
        return name

    class Meta:
        model = Tag
        fields = '__all__'


# --------------------------------- Inlines --------------------------------- #


class ParameterInline(admin.TabularInline):
    """
    InfluxDB does not allow to change parameter type therefore parameter
    should not be changed.
    """

    model = Parameter
    extra = 0
    ordering = 'oid', 'name'
    form = AlwaysValidForm
    readonly_fields = ('group', 'name', 'type',
                       'description', 'indexing', 'oid')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class AddParameterInline(admin.TabularInline):
    model = Parameter
    extra = 1
    form = ParameterCollisionForm
    verbose_name = _('Add Parameter')
    verbose_name_plural = _('Add Parameters')
    classes = ['collapse']

    def get_queryset(self, request):
        """
        Inline responsible only for creating new instances should have
        queryset limited to empty one.
        """
        return super().get_queryset(request).none()

    def has_delete_permission(self, request, obj=None):
        return False


class InstanceInline(admin.TabularInline):
    model = Instance
    form = InstanceForm
    extra = 0
    ordering = 'group__oid', 'oid'


class TagValueInline(admin.TabularInline):
    model = TagValue
    extra = 0
    ordering = 'tag_id',


class TagAdmin(admin.ModelAdmin):
    form = TagForm

    def has_change_permission(self, request, obj=None):
        return not obj

    def has_delete_permission(self, request, obj=None):
        return False

    def get_model_perms(self, request) -> dict:
        """
        By returning an empty dict Tag model gets hidden from main admin
        panel but is accessible through related Host model and its admin
        page.
        """
        return {}


# ------------------------------- ModelAdmins ------------------------------- #


class HostAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip', 'community', 'port')
    fieldsets = [
        (
            None,
            {
                'fields': ['name', 'ip', 'description']
            }
        ),
        (
            _('SNMP'),
            {
                'fields': ['community', 'port']
            }
        )
    ]
    ordering = 'name',
    inlines = [
        InstanceInline, TagValueInline
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('name',)
        return self.readonly_fields


class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'oid', 'type', 'in_use')
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
                'fields': ['oid']
            }
        )
    ]
    ordering = 'oid',
    inlines = [ParameterInline, AddParameterInline]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('name', 'type')
        return self.readonly_fields

    def in_use(self, obj: Group) -> bool:
        """
        Indicates if the group is enabled for at least one host.

        :param obj: group which usage is to be verified
        :return: groups's state of usage
        """
        return obj.hosts.exists()
    in_use.boolean = True
    in_use.short_description = _('in use?')


admin.site.register(Group, GroupAdmin)
admin.site.register(Host, HostAdmin)
admin.site.register(Tag, TagAdmin)

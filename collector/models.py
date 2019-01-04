from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _

from . import constants

oid_validator = validators.RegexValidator(regex=r'^(\d+\.)+\d+$')


class Group(models.Model):
    SCALAR = False
    TABULAR = True
    TYPES = (
        (SCALAR, _('scalar')),
        (TABULAR, _('tabular'))
    )
    name = models.CharField(
        verbose_name=_('name'),
        primary_key=True,
        max_length=constants.NAME_MAX_LENGTH,
        help_text=_('Unique and unchangeable group identifier.')
    )
    type = models.BooleanField(
        verbose_name=_('type'),
        blank=False,
        choices=TYPES,
        help_text=_('SNMP parameters are of scalar or tabular type. '
                    'Please verify right settings with documentation.')
    )
    description = models.TextField(
        verbose_name=_('description'),
        blank=True,
        help_text=_('A few words to show e.g. group purpose or meaning.')
    )
    oid = models.CharField(
        verbose_name=_('OID'),
        max_length=constants.OID_MAX_LENGTH,
        blank=True,
        db_index=True,
        help_text=_('Object identifier uniquely identifies group of monitored '
                    'parameters. <b>Usually full OID without two last '
                    'parts.</b>'),
        validators=(oid_validator,)
    )

    class Meta:
        verbose_name = _('Group')
        verbose_name_plural = _('Groups')

    def __str__(self):
        return self.name


class Parameter(models.Model):
    FLOAT = 0
    INTEGER = 1
    STRING = 2
    BOOLEAN = 3
    TYPES = (
        (FLOAT, _('float')),
        (INTEGER, _('integer')),
        (STRING, _('string')),
        (BOOLEAN, _('boolean'))
    )
    group = models.ForeignKey(
        to=Group,
        on_delete=models.CASCADE,
        related_name='parameters',
        related_query_name='parameter',
        verbose_name=_('group')
    )
    name = models.CharField(
        verbose_name=_('name'),
        primary_key=True,
        max_length=constants.NAME_MAX_LENGTH,
        help_text=_('Unique and unchangeable parameter identifier.')
    )
    type = models.PositiveSmallIntegerField(
        verbose_name=_('type'),
        choices=TYPES,
        help_text=_('Unchangeable parameter type.')
    )
    description = models.TextField(
        verbose_name=_('description'),
        blank=True,
        help_text=_('A few words to show e.g. parameter purpose or meaning.')
    )
    indexing = models.BooleanField(
        verbose_name=_('indexing'),
        blank=True,
        default=False,
        help_text=_('Should this parameter be used as a indexing tag?\n'
                    '⚠️ Using too many parameters as tags can have '
                    'significant performance impact.️')
    )
    oid = models.PositiveIntegerField(
        verbose_name=_('OID'),
        blank=True,
        default=0,
        help_text=_('Last but one OID part.')
    )

    class Meta:
        verbose_name = _('Parameter')
        verbose_name_plural = _('Parameters')

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        verbose_name=_('name'),
        primary_key=True,
        max_length=constants.NAME_MAX_LENGTH
    )

    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')

    def __str__(self):
        return self.name


class Host(models.Model):
    name = models.CharField(
        verbose_name=_('name'),
        primary_key=True,
        max_length=constants.NAME_MAX_LENGTH,
        help_text=_('Unique and unchangeable host identifier.')
    )
    ip = models.GenericIPAddressField(
        verbose_name=_('IP address'),
        help_text=_('Internet Protocol version 4 or 6 address.')
    )
    description = models.TextField(
        verbose_name=_('description'),
        blank=True,
        help_text=_('A few words to show e.g. host purpose or location.')
    )
    groups = models.ManyToManyField(
        to=Group,
        related_name='hosts',
        related_query_name='host',
        through='Instance',
        verbose_name=_('groups')
    )
    community = models.CharField(
        verbose_name=_('community name'),
        max_length=constants.NAME_MAX_LENGTH,
        blank=True,
        db_index=True,
        help_text=_('SNMP mandates that the SNMP agents should accept request '
                    'messages only if the community string in the message '
                    'matches its community name. '
                    '<b>Ensure same value is set on the device.</b>')
    )
    port = models.PositiveSmallIntegerField(
        verbose_name=_('port'),
        default=161,
        help_text=_('Set SNMP GET port. '
                    '<b>Ensure same value is set on the device.</b>')
    )
    tags = models.ManyToManyField(
        to=Tag,
        related_name='hosts',
        related_query_name='host',
        through='TagValue',
        verbose_name=_('tags')
    )

    class Meta:
        verbose_name = _('Host')
        verbose_name_plural = _('Hosts')

    def __str__(self):
        return self.name


class Instance(models.Model):
    group = models.ForeignKey(
        to=Group,
        on_delete=models.CASCADE,
        related_name='instances',
        related_query_name='instance',
        verbose_name=_('group')
    )
    host = models.ForeignKey(
        to=Host,
        on_delete=models.CASCADE,
        related_name='instances',
        related_query_name='instance',
        verbose_name=_('host')
    )
    oid = models.PositiveIntegerField(
        verbose_name=_('OID'),
        blank=True,
        default=0,
        help_text=_('Last OID part.')
    )
    name = models.CharField(
        verbose_name=_('name'),
        max_length=constants.NAME_MAX_LENGTH,
        blank=True,
        help_text=_('Instance identifier. If non-empty is used as tag.')
    )

    class Meta:
        unique_together = ('group', 'host', 'oid')
        verbose_name = _('Instance')
        verbose_name_plural = _('Instances')

    def __str__(self):
        return '{obj.name}@{obj.group_id}'.format(obj=self)


class TagValue(models.Model):
    tag = models.ForeignKey(
        to=Tag,
        on_delete=models.CASCADE,
        related_name='values',
        related_query_name='value',
        verbose_name=_('tag')
    )
    host = models.ForeignKey(
        to=Host,
        on_delete=models.CASCADE,
        related_name='tag_values',
        related_query_name='tag_value',
        verbose_name=_('host')
    )
    value = models.CharField(
        verbose_name=_('value'),
        max_length=constants.NAME_MAX_LENGTH
    )

    class Meta:
        verbose_name = _('Tag Value')
        verbose_name_plural = _('Tag Values')

    def __str__(self):
        return '{obj.tag_id} = {obj.value}'.format(obj=self)

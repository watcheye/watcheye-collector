from django.db import models
from django.utils.translation import gettext_lazy as _

from . import constants


class Parameter(models.Model):
    FLOAT = 0
    INTEGER = 1
    STRING = 2
    BOOLEAN = 3
    TYPES = (
        (FLOAT, _('float')),
        (INTEGER, _('integer')),
        (STRING, _('string')),
        (BOOLEAN, _('boolean')),
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
    oid = models.CharField(
        verbose_name=_('OID'),
        max_length=constants.OID_MAX_LENGTH,
        blank=True,
        db_index=True,
        help_text=_('Object Identifier uniquely identifies monitored '
                    'parameter.')
    )

    class Meta:
        verbose_name = _('Parameter')
        verbose_name_plural = _('Parameters')

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
    parameters = models.ManyToManyField(
        to=Parameter,
        related_name='hosts',
        related_query_name='host',
        verbose_name=_('parameters'),
        help_text=_('Choosing parameters enables their collection for the '
                    'host.<br/>')
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

    class Meta:
        verbose_name = _('Host')
        verbose_name_plural = _('Hosts')

    def __str__(self):
        return self.name

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CollectorConfig(AppConfig):
    name = 'collector'
    verbose_name = _('collector')

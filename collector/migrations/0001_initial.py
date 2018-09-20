from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Parameter',
            fields=[
                (
                    'name',
                    models.CharField(
                        help_text='Unique and unchangeable parameter '
                                  'identifier.',
                        max_length=32,
                        primary_key=True,
                        serialize=False,
                        verbose_name='name'
                    )
                ),
                (
                    'type',
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, 'float'),
                            (1, 'integer'),
                            (2, 'string'),
                            (3, 'boolean')
                        ],
                        help_text='Unchangeable parameter type.',
                        verbose_name='type'
                    )
                ),
                (
                    'description',
                    models.TextField(
                        blank=True,
                        help_text='A few words to show e.g. parameter purpose '
                                  'or meaning.',
                        verbose_name='description'
                    )
                ),
                (
                    'oid',
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text='Object Identifier uniquely identifies '
                                  'monitored parameter.',
                        max_length=64,
                        verbose_name='OID'
                    )
                ),
            ],
            options={
                'verbose_name': 'Parameter',
                'verbose_name_plural': 'Parameters',
            },
        ),
        migrations.CreateModel(
            name='Host',
            fields=[
                (
                    'name',
                    models.CharField(
                        help_text='Unique and unchangeable host identifier.',
                        max_length=32,
                        primary_key=True,
                        serialize=False,
                        verbose_name='name'
                    )
                ),
                (
                    'ip',
                    models.GenericIPAddressField(
                        help_text='Internet Protocol version 4 or 6 address.',
                        verbose_name='IP address'
                    )
                ),
                (
                    'description',
                    models.TextField(
                        blank=True,
                        help_text='A few words to show e.g. host purpose or '
                                  'location.',
                        verbose_name='description'
                    )
                ),
                (
                    'parameters',
                    models.ManyToManyField(
                        help_text='Choosing parameters enables their '
                                  'collection for the host.<br/>',
                        related_name='hosts',
                        related_query_name='host',
                        to='collector.Parameter',
                        verbose_name='parameters'
                    )
                ),
                (
                    'community',
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text='SNMP mandates that the SNMP agents should '
                                  'accept request messages only if the '
                                  'community string in the message matches '
                                  'its community name. <b>Ensure same value '
                                  'is set on the device.</b>',
                        max_length=32,
                        verbose_name='community name'
                    )
                ),
                (
                    'port',
                    models.PositiveSmallIntegerField(
                        default=161,
                        help_text='Set SNMP GET port. <b>Ensure same value is '
                                  'set on the device.</b>',
                        verbose_name='port'
                    )
                )
            ],
            options={
                'verbose_name': 'Host',
                'verbose_name_plural': 'Hosts'
            }
        )
    ]

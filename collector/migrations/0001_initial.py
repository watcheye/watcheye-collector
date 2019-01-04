import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                (
                    'name',
                    models.CharField(
                        help_text='Unique and unchangeable group identifier.',
                        max_length=64,
                        primary_key=True,
                        serialize=False,
                        verbose_name='name'
                    )
                ),
                (
                    'type',
                    models.BooleanField(
                        choices=[
                            (False, 'scalar'),
                            (True, 'tabular')
                        ],
                        help_text='SNMP parameters are of scalar or tabular '
                                  'type. Please verify right settings with '
                                  'documentation.',
                        verbose_name='type'
                    )
                ),
                (
                    'description',
                    models.TextField(
                        blank=True,
                        help_text='A few words to show e.g. group purpose or '
                                  'meaning.',
                        verbose_name='description'
                    )
                ),
                (
                    'oid',
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text='Object identifier uniquely identifies '
                                  'group of monitored parameters. <b>Usually '
                                  'full OID without two last parts.</b>',
                        max_length=64,
                        validators=[
                            django.core.validators.RegexValidator(
                                regex='^(\\d+\\.)+\\d+$'
                            )
                        ],
                        verbose_name='OID'
                    )
                )
            ],
            options={
                'verbose_name': 'Group',
                'verbose_name_plural': 'Groups'
            }
        ),
        migrations.CreateModel(
            name='Host',
            fields=[
                (
                    'name',
                    models.CharField(
                        help_text='Unique and unchangeable host identifier.',
                        max_length=64,
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
                    'community',
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text='SNMP mandates that the SNMP agents should '
                                  'accept request messages only if the '
                                  'community string in the message matches '
                                  'its community name. <b>Ensure same value '
                                  'is set on the device.</b>',
                        max_length=64,
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
        ),
        migrations.CreateModel(
            name='Instance',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                (
                    'oid',
                    models.PositiveIntegerField(
                        blank=True,
                        default=0,
                        help_text='Last OID part.',
                        verbose_name='OID'
                    )
                ),
                (
                    'name',
                    models.CharField(
                        blank=True,
                        help_text='Instance identifier. If non-empty is used '
                                  'as tag.',
                        max_length=64,
                        verbose_name='name'
                    )
                ),
                (
                    'group',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='instances',
                        related_query_name='instance',
                        to='collector.Group',
                        verbose_name='group'
                    )
                ),
                (
                    'host',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='instances',
                        related_query_name='instance',
                        to='collector.Host',
                        verbose_name='host'
                    )
                )
            ],
            options={
                'verbose_name': 'Instance',
                'verbose_name_plural': 'Instances'
            }
        ),
        migrations.CreateModel(
            name='Parameter',
            fields=[
                (
                    'name',
                    models.CharField(
                        help_text='Unique and unchangeable parameter '
                                  'identifier.',
                        max_length=64,
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
                    'indexing',
                    models.BooleanField(
                        blank=True,
                        default=False,
                        help_text='Should this parameter be used as a '
                                  'indexing tag?\n⚠️ Using too many '
                                  'parameters as tags can have significant '
                                  'performance impact.️',
                        verbose_name='indexing'
                    )
                ),
                (
                    'oid',
                    models.PositiveIntegerField(
                        blank=True,
                        default=0,
                        help_text='Last but one OID part.',
                        verbose_name='OID'
                    )
                ),
                (
                    'group',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='parameters',
                        related_query_name='parameter',
                        to='collector.Group',
                        verbose_name='group'
                    )
                )
            ],
            options={
                'verbose_name': 'Parameter',
                'verbose_name_plural': 'Parameters'
            }
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                (
                    'name',
                    models.CharField(
                        max_length=64,
                        primary_key=True,
                        serialize=False,
                        verbose_name='name'
                    )
                )
            ],
            options={
                'verbose_name': 'Tag',
                'verbose_name_plural': 'Tags'
            }
        ),
        migrations.CreateModel(
            name='TagValue',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                (
                    'value',
                    models.CharField(
                        max_length=64,
                        verbose_name='value'
                    )
                ),
                (
                    'host',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tag_values',
                        related_query_name='tag_value',
                        to='collector.Host',
                        verbose_name='host'
                    )
                ),
                (
                    'tag',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='values',
                        related_query_name='value',
                        to='collector.Tag',
                        verbose_name='tag'
                    )
                )
            ],
            options={
                'verbose_name': 'Tag Value',
                'verbose_name_plural': 'Tag Values'
            }
        ),
        migrations.AddField(
            model_name='host',
            name='groups',
            field=models.ManyToManyField(
                related_name='hosts',
                related_query_name='host',
                through='collector.Instance',
                to='collector.Group',
                verbose_name='groups'
            )
        ),
        migrations.AddField(
            model_name='host',
            name='tags',
            field=models.ManyToManyField(
                related_name='hosts',
                related_query_name='host',
                through='collector.TagValue',
                to='collector.Tag',
                verbose_name='tags'
            )
        ),
        migrations.AlterUniqueTogether(
            name='instance',
            unique_together={('group', 'host', 'oid')}
        )
    ]

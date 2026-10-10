# Django Migration Imports

import django.db.models.deletion
from django.db import migrations, models


# Initial Vital Reading Database Migration

class Migration(migrations.Migration):
    initial = True

    # Migration Dependencies

    dependencies = [
        ('kiosk', '0001_initial'),
    ]

    # Database Operations

    operations = [

        # Vital Reading Model

        migrations.CreateModel(
            name='VitalReading',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spo2', models.FloatField(help_text='Blood oxygen saturation percentage')),
                ('heart_rate', models.IntegerField(help_text='Heart rate in BPM')),
                ('temperature', models.FloatField(blank=True, help_text='Body temperature in Celsius', null=True)),
                ('is_valid', models.BooleanField(default=True, help_text='Whether the reading passed quality check')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vitals', to='kiosk.patientsession')),
            ],

            # Model Meta Confi.

            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
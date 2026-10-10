# Django Migration Imports

from django.db import migrations, models


# Daily Token Counter Migration

class Migration(migrations.Migration):
    """
    Creates the DailyTokenCounter model for tracking daily
    patient token numbers.
    """

    # Migration Dependencies

    dependencies = [
        ('kiosk', '0001_initial'),
    ]

    # Database Operations

    operations = [
        migrations.CreateModel(
            name='DailyTokenCounter',
            fields=[
                ('date', models.DateField(primary_key=True, serialize=False)),
                ('last_token', models.IntegerField(default=0)),
            ],
        ),
    ]
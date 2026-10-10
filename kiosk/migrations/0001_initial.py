# Django Migration Imports

import django.db.models.deletion
import uuid
from django.db import migrations, models


# Initial Database Migration

class Migration(migrations.Migration):
    """
    Initial database migration for the Kiosk application.
    """

    initial = True

    # Migration Dependencies

    dependencies = [
    ]

    # Database Operations

    operations = [

        # Patient Session Model

        migrations.CreateModel(
            name='PatientSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('active', 'Active'), ('completed', 'Completed'), ('abandoned', 'Abandoned')], default='active', max_length=20)),
                ('language', models.CharField(choices=[('en', 'English'), ('hi', 'Hindi'), ('ta', 'Tamil'), ('bn', 'Bengali'), ('mr', 'Marathi')], default='en', max_length=5)),
                ('consent_given', models.BooleanField(default=False)),
                ('abha_id', models.CharField(blank=True, default='', max_length=50)),
                ('chief_complaints', models.JSONField(blank=True, default=list)),
                ('selected_body_regions', models.JSONField(blank=True, default=list)),
                ('token_number', models.IntegerField(blank=True, null=True)),
                ('red_flags', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),

        # Document Upload Model

        migrations.CreateModel(
            name='DocumentUpload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='documents/%Y/%m/%d/')),
                ('raw_ocr_text', models.TextField(blank=True, default='')),
                ('extracted_entities', models.JSONField(blank=True, default=dict)),
                ('ocr_provider', models.CharField(blank=True, default='', max_length=30)),
                ('ocr_confidence', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='kiosk.patientsession')),
            ],
        ),

        # Conversation Log Model

        migrations.CreateModel(
            name='ConversationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('system', 'System'), ('assistant', 'Assistant'), ('user', 'User')], max_length=10)),
                ('content', models.TextField()),
                ('input_type', models.CharField(choices=[('text', 'Text'), ('voice', 'Voice'), ('button', 'Button'), ('body_map', 'Body Map')], default='text', max_length=10)),
                ('confidence', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='kiosk.patientsession')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),

        # Clinical Summary Model

        migrations.CreateModel(
            name='ClinicalSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('summary_text', models.TextField()),
                ('structured_data', models.JSONField(blank=True, default=dict)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='summary', to='kiosk.patientsession')),
            ],
            options={
                'verbose_name_plural': 'Clinical summaries',
            },
        ),
    ]
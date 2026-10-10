# Django Imports

from django.apps import AppConfig


# Sensors Application Confi.

class SensorsConfig(AppConfig):
    # Default Primary Key Confi.

    default_auto_field = 'django.db.models.BigAutoField'

    # Application Name

    name = 'sensors'
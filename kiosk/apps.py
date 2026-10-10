# Django Imports

from django.apps import AppConfig


# Kiosk Application Confi.

class KioskConfig(AppConfig):
    # Default Primary Key Confi.

    default_auto_field = 'django.db.models.BigAutoField'

    # Application Name

    name = 'kiosk'
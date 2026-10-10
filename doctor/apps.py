# Django Imports

from django.apps import AppConfig


# Doctor Application Confi.

class DoctorConfig(AppConfig):
    """
    Configuration class for the Doctor application.
    """

    # Default Primary Key Confi.

    default_auto_field = 'django.db.models.BigAutoField'

    # Application Name

    name = 'doctor'
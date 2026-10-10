# Django Imports

from django.db import models


# Medicine Model Definition

class Medicine(models.Model):
    # Database Fields

    brand_name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True, default='')
    dosage_form = models.CharField(max_length=100, blank=True, default='')
    strength = models.CharField(max_length=100, blank=True, default='')
    manufacturer = models.CharField(max_length=200, blank=True, default='')

    # Model Meta Confi.

    class Meta:
        ordering = ['brand_name']

    # String Representation

    def __str__(self):
        return f"{self.brand_name} ({self.generic_name})"
# Django Imports

from django.db import models


# Vital Reading Model Definition

class VitalReading(models.Model):
    # Database Fields

    session = models.ForeignKey(
        'kiosk.PatientSession',
        on_delete=models.CASCADE,
        related_name='vitals'
    )
    spo2 = models.FloatField(help_text='Blood oxygen saturation percentage')
    heart_rate = models.IntegerField(help_text='Heart rate in BPM')
    systolic_bp = models.IntegerField(null=True, blank=True, help_text='Systolic blood pressure (mmHg)')
    diastolic_bp = models.IntegerField(null=True, blank=True, help_text='Diastolic blood pressure (mmHg)')
    temperature = models.FloatField(null=True, blank=True, help_text='Body temperature in Celsius')
    is_abnormal = models.BooleanField(default=False, help_text='Whether any vital is outside normal range')
    severity = models.CharField(
        max_length=20,
        choices=[('normal', 'Normal'), ('elevated', 'Elevated'), ('critical', 'Critical')],
        default='normal',
        help_text='Triage severity based on vital thresholds'
    )
    provenance = models.CharField(
        max_length=30,
        choices=[('patient_reported', 'Patient Reported'), ('sensor', 'Sensor Telemetry')],
        default='sensor'
    )
    is_valid = models.BooleanField(default=True, help_text='Whether the reading passed quality check')
    created_at = models.DateTimeField(auto_now_add=True)

    # Model Meta Confi.

    class Meta:
        ordering = ['-created_at']

    # String Representation

    def __str__(self):
        bp_str = f", BP: {self.systolic_bp}/{self.diastolic_bp}" if self.systolic_bp and self.diastolic_bp else ""
        return f"SpO₂: {self.spo2}%, HR: {self.heart_rate} BPM{bp_str} [{self.severity}]"

    def compute_severity(self):
        """
        Thresholds:
        SpO2 < 92 → critical
        BP > 140/90 → elevated, > 180/120 → critical
        Temp > 38.0 → elevated, > 39.5 → critical
        Pulse < 50 or > 120 → elevated
        """
        sev = 'normal'
        abnormal = False

        # Pulse check
        if self.heart_rate < 50 or self.heart_rate > 120:
            sev = 'elevated'
            abnormal = True

        # Temp check
        if self.temperature:
            if self.temperature > 39.5:
                sev = 'critical'
                abnormal = True
            elif self.temperature > 38.0:
                if sev != 'critical':
                    sev = 'elevated'
                abnormal = True

        # Blood Pressure check
        if self.systolic_bp and self.diastolic_bp:
            if self.systolic_bp > 180 or self.diastolic_bp > 120:
                sev = 'critical'
                abnormal = True
            elif self.systolic_bp > 140 or self.diastolic_bp > 90:
                if sev != 'critical':
                    sev = 'elevated'
                abnormal = True

        # SpO2 check (overrides to critical if < 92)
        if self.spo2 < 92:
            sev = 'critical'
            abnormal = True
        elif self.spo2 < 95:
            if sev != 'critical':
                sev = 'elevated'
            abnormal = True

        return abnormal, sev

    def save(self, *args, **kwargs):
        abnormal, sev = self.compute_severity()
        self.is_abnormal = abnormal
        self.severity = sev
        super().save(*args, **kwargs)

    @property
    def abnormal_details(self):
        abnormal = {}
        if self.spo2 < 92:
            abnormal['spo2'] = 'critical_low'
        elif self.spo2 < 95:
            abnormal['spo2'] = 'low'

        if self.heart_rate > 120:
            abnormal['heart_rate'] = 'high'
        elif self.heart_rate < 50:
            abnormal['heart_rate'] = 'low'

        if self.temperature:
            if self.temperature > 39.5:
                abnormal['temperature'] = 'critical_high'
            elif self.temperature > 38.0:
                abnormal['temperature'] = 'high'

        if self.systolic_bp and self.diastolic_bp:
            if self.systolic_bp > 180 or self.diastolic_bp > 120:
                abnormal['blood_pressure'] = 'critical_high'
            elif self.systolic_bp > 140 or self.diastolic_bp > 90:
                abnormal['blood_pressure'] = 'elevated'

        return abnormal
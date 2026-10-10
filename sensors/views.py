# Imports

import uuid
import math
import logging
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from kiosk.models import PatientSession
from .models import VitalReading
from .serializers import VitalReadingSerializer


# Logger Confi.
logger = logging.getLogger(__name__)


# Sensor Rate Throttle Confi.
class SensorRateThrottle(AnonRateThrottle):
    scope = 'sensor'

# Patient Session Helper
def get_active_session_or_response(session_id):
    if not session_id:
        return None, Response(
            {'error': 'session_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        if isinstance(session_id, str):
            uuid_obj = uuid.UUID(session_id)
        else:
            uuid_obj = session_id

    except (ValueError, TypeError, AttributeError):
        return None, Response(
            {'error': 'Invalid session_id format.'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        session = PatientSession.objects.get(id=uuid_obj)

    except PatientSession.DoesNotExist:
        return None, Response(
            {'error': 'Session not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if session.status != 'active':
        return None, Response(
            {'error': 'Session is no longer active.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    return session, None


# Vitals POST Endpoint View
class VitalsPostView(APIView):
    """
    POST /api/vitals/post/ — Accept vitals from ESP32 or kiosk sensors.
    Supports optional device authentication header when SENSOR_AUTH_REQUIRED=True.
    """

    # API Permissions & Throttling
    permission_classes = [AllowAny]
    throttle_classes = [SensorRateThrottle]

    # HTTP POST Request Handler
    def post(self, request):
        """
        Accepts and validates vital readings submitted by the sensor device.
        """
        # Device Authentication
        # Device Authentication (when SENSOR_AUTH_REQUIRED=True)
        if getattr(settings, 'SENSOR_AUTH_REQUIRED', False):
            device_token = request.headers.get('X-Sensor-Secret', '') or request.data.get('sensor_secret', '')
            expected_token = getattr(settings, 'SENSOR_SECRET_KEY', '')

            if not device_token or device_token != expected_token:
                logger.warning("Unauthorized ESP32 sensor submission attempt.")

                return Response(
                    {'error': 'Device authentication failed.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # Extract Vital Reading Payload
        session_id = request.data.get('session_id')
        spo2 = request.data.get('spo2')
        heart_rate = request.data.get('heart_rate')
        systolic_bp = request.data.get('systolic_bp')
        diastolic_bp = request.data.get('diastolic_bp')
        temperature = request.data.get('temperature')
        provenance = request.data.get('provenance', 'sensor')

        # Validate Required Vital Parameters
        if spo2 is None or heart_rate is None:
            return Response(
                {'error': 'spo2 and heart_rate are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate Patient Session
        session, error_response = get_active_session_or_response(session_id)

        if error_response:
            return error_response

        try:
            spo2_val = float(spo2)
            hr_val = float(heart_rate)
            temp_val = float(temperature) if temperature is not None else None
            sys_val = int(systolic_bp) if systolic_bp is not None else None
            dia_val = int(diastolic_bp) if diastolic_bp is not None else None

            # Validate SpO₂ Value
            if math.isnan(spo2_val) or math.isinf(spo2_val):
                raise ValueError("spo2 cannot be NaN or Infinite.")

            # Validate Heart Rate Value
            if math.isnan(hr_val) or math.isinf(hr_val):
                raise ValueError("heart_rate cannot be NaN or Infinite.")

            # Validate Temperature Value
            if temp_val is not None and (math.isnan(temp_val) or math.isinf(temp_val)):
                raise ValueError("temperature cannot be NaN or Infinite.")

        except (ValueError, TypeError):
            return Response(
                {'error': 'vitals values must be valid numbers.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate Clinical Ranges
        is_valid = True

        if not (50.0 <= spo2_val <= 100.0):
            is_valid = False

        if not (20.0 <= hr_val <= 250.0):
            is_valid = False

        if temp_val is not None and not (25.0 <= temp_val <= 45.0):
            is_valid = False

        # Create Vital Reading Record
        reading = VitalReading.objects.create(
            session=session,
            spo2=spo2_val,
            heart_rate=int(hr_val),
            systolic_bp=sys_val,
            diastolic_bp=dia_val,
            temperature=temp_val,
            provenance=provenance if provenance in ('patient_reported', 'sensor') else 'sensor',
            is_valid=is_valid,
        )

        # Detect AVS
        abnormal = reading.is_abnormal

        if abnormal:
            logger.warning(
                f"Abnormal vitals for session {session_id}: {reading.severity} ({reading.abnormal_details})"
            )

        return Response({
            'reading_id': reading.id,
            'is_valid': is_valid,
            'is_abnormal': reading.is_abnormal,
            'severity': reading.severity,
            'abnormal_details': reading.abnormal_details,
        }, status=status.HTTP_201_CREATED)


# Latest Vitals GET Endpoint View
class LatestVitalsView(APIView):
    """
    GET /api/vitals/latest/<session_id>/ — Get latest valid vitals.
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            uuid_obj = uuid.UUID(str(session_id))
            session = PatientSession.objects.get(id=uuid_obj)
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response(
                {'error': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        latest = VitalReading.objects.filter(
            session=session,
            is_valid=True
        ).order_by('-created_at').first()

        if not latest:
            return Response(
                {'error': 'No vitals recorded yet.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(VitalReadingSerializer(latest).data)


class FlaggedVitalsView(APIView):
    """
    GET /api/vitals/flagged/<session_id>/ — Get abnormal / elevated / critical vitals.
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            uuid_obj = uuid.UUID(str(session_id))
            session = PatientSession.objects.get(id=uuid_obj)
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response(
                {'error': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        flagged = VitalReading.objects.filter(
            session=session,
            is_abnormal=True
        ).order_by('-created_at')

        return Response({
            'session_id': str(session.id),
            'count': flagged.count(),
            'flagged_readings': VitalReadingSerializer(flagged, many=True).data,
            'highest_severity': 'critical' if flagged.filter(severity='critical').exists() else ('elevated' if flagged.filter(severity='elevated').exists() else 'normal')
        })
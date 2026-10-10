import os
import sys
import logging
from kiosk.models import ConversationLog

logger = logging.getLogger(__name__)

# Ensure parent root directory (where body_pointing.py resides) is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Navigate up to workspace root directory: medikiosk/kiosk/utils -> medikiosk/kiosk -> medikiosk -> workspace_root
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)


def execute_body_pointing(session=None, timeout_seconds=20):
    """
    Executes the MediaPipe body region tracking script (body_pointing.py).
    Updates the session's selected body regions and logs the action to ConversationLog.
    """
    try:
        import body_pointing
        result = body_pointing.run_body_pointing(timeout_seconds=timeout_seconds, show_window=True)

        if result.get('success') and session:
            region = result.get('region')
            if region and region not in ('unknown', 'Searching...', 'No finger detected'):
                # Update selected body regions list
                regions = session.selected_body_regions or []
                if region not in regions:
                    regions.append(region)
                    session.selected_body_regions = regions
                    session.save()

                # V1: Automatically append region to StructuredHistory.hpi.location and associated_symptoms
                try:
                    from kiosk.models import StructuredHistory
                    hist, _ = StructuredHistory.objects.get_or_create(session=session)
                    hpi = hist.hpi or {}
                    curr_loc = hpi.get('location', '')
                    if curr_loc and curr_loc != 'unspecified':
                        if region not in curr_loc:
                            hpi['location'] = f"{curr_loc}, {region}"
                    else:
                        hpi['location'] = region

                    assoc = hpi.get('associated_symptoms', [])
                    region_symptom = {'text': f"Pain at {region}", 'provenance': 'patient_reported'}
                    if not any(isinstance(x, dict) and x.get('text') == region_symptom['text'] for x in assoc):
                        assoc.append(region_symptom)
                    hpi['associated_symptoms'] = assoc
                    hist.hpi = hpi
                    hist.save()
                except Exception as hist_err:
                    logger.warning(f"Could not update StructuredHistory for body pointing: {hist_err}")

                # Log to conversation history
                ConversationLog.objects.create(
                    session=session,
                    role='user',
                    content=f"I pointed to my {region}.",
                    input_type='body_pointing'
                )
                logger.info(f"Body pointing captured region '{region}' for session {session.id}")

        return result
    except Exception as e:
        logger.error(f"Error executing body pointing tracker: {e}", exc_info=True)
        return {'success': False, 'region': 'unknown', 'error': str(e)}


def append_body_region_to_history(session, region: str, provenance: str = 'patient_reported'):
    """Helper to attach a confirmed or pointed body region to StructuredHistory with provenance."""
    from kiosk.models import StructuredHistory
    hist, _ = StructuredHistory.objects.get_or_create(session=session)
    hpi = hist.hpi or {}
    curr_loc = hpi.get('location', '')
    if curr_loc and curr_loc != 'unspecified':
        if region not in curr_loc:
            hpi['location'] = f"{curr_loc}, {region}"
    else:
        hpi['location'] = region

    assoc = hpi.get('associated_symptoms', [])
    region_symptom = {'text': f"Pain at {region}", 'provenance': provenance}
    if not any(isinstance(x, dict) and x.get('text') == region_symptom['text'] for x in assoc):
        assoc.append(region_symptom)
    hpi['associated_symptoms'] = assoc
    hist.hpi = hpi
    hist.save()
    return hist


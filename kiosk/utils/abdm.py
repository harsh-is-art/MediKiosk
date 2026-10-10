"""Mock ABDM (Ayushman Bharat Digital Mission) integration."""
import uuid
import logging

logger = logging.getLogger(__name__)


def push_to_abdm(summary):
    """
    Mock function — logs the summary but does not call external API.
    In production, this would push to ABDM's Health Information Exchange.
    """
    logger.info(f"[MOCK ABDM] Would push summary for session {summary.session_id}")
    logger.info(f"[MOCK ABDM] Summary text: {summary.summary_text[:100]}...")
    return {'status': 'mock_success', 'transaction_id': str(uuid.uuid4())}


def generate_mock_abha_id():
    """Generate a dummy ABHA ID for demo purposes."""
    import random
    digits = ''.join([str(random.randint(0, 9)) for _ in range(14)])
    return f"{digits[:2]}-{digits[2:6]}-{digits[6:10]}-{digits[10:14]}"

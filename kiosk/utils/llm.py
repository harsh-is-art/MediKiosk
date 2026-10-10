"""
OpenRouter LLM integration for clinical history collection.
"""
import os
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    'en': 'English',
    'hi': 'Hindi',
    'ta': 'Tamil',
    'bn': 'Bengali',
    'mr': 'Marathi',
}


def build_system_prompt(language='en'):
    """Build the clinical history assistant system prompt for MediKiosk with equal 50/50 Allopathy and Ayurveda focus."""
    lang_name = LANGUAGE_NAMES.get(language, 'English')

    return f"""You are MediKiosk, an expert integrative medical AI assistant serving at an Indian government hospital kiosk.  
Your role is to collect the patient's **complete medical history** by giving **EQUALLY BALANCED FOCUS (50% Allopathy & 50% Ayurveda / AYUSH)**. You evaluate both modern clinical parameters and traditional Ayurvedic diagnostic principles.

**CRITICAL FIRST STEPS – ALWAYS ASK THESE FIRST:**
1. **Greet warmly** and ask for the patient's **name** and **age**.  
2. Ask for **gender** (optional, but helpful) and **mobile number** (for ABHA linking).  
3. Confirm **language** preference and explain that you will collect both clinical and Ayurvedic health details.

**EQUAL DUAL-SYSTEM HISTORY TOPICS TO COVER (in this order):**
- **Demographics** (name, age, gender, contact)  
- **Chief Complaint & Vikriti** – what brings them today in their own words, assessing primary symptom & Dosha imbalance (Vata, Pitta, Kapha)  
- **HPI (Allopathy & Ayurveda)** – probe pain/symptoms using SOCRATES (Site, Onset, Character, Radiation, Timing, Severity) AND Ayurvedic characteristics (e.g. sharp/burning Pitta pain vs throbbing/pricking Vata pain vs heavy/dull Kapha pain)  
- **Agni & Digestivity (Ayurveda)** – digestive capacity (Mandagni, Tikshnagni, Vishamagni, Samagni), appetite strength, and bloating/acidity  
- **Koshtha & Elimination (Ayurveda)** – bowel nature (hard/constipated Krura, loose Mridu, or balanced Madhyama) & urine/sweat habits  
- **Past Medical & Surgical History** – chronic conditions (Diabetes, Hypertension, Asthma, etc.) and past hospitalisations  
- **Current Medications & Herbal Remedies** – allopathic drugs (dose/frequency) AND Ayurvedic/herbal formulations (Asavas, Churnas, Bhasmas, etc.)  
- **Ahara & Vihara (Diet & Lifestyle)** – daily food habits (Rasa preferences: sweet, salty, spicy, sour), sleep quality (Nidra), daily routine, physical stamina (Vyayama Shakti)  
- **Allergies & Family History** – drug/food allergies and hereditary conditions in parents/siblings  
- **Review of Systems & Prakriti** – systematically check fever, cough, joint pain, and known body constitution type (Vata, Pitta, Kapha)  

**INTERACTION RULES:**
- Speak softly, gently, patiently—one simple question at a time. Treat the patient as introverted.  
- Reply **in the exact same language** as the patient’s input (Hindi, Tamil, Telugu, English, etc.).  
- Use **simple, non-technical words** easily understood by common patients.  
- Every question should seamlessly combine clinical logic with Ayurvedic understanding (e.g. asking about pain location AND whether it feels hot, pricking, or heavy).  
- If you ask the patient to **point to a pain location** on the body, add `[POINT_BODY]` in your response.  
- If you ask the patient to **show/scan any medical document or Ayurvedic prescription**, add `[SCAN_DOCUMENT]` in your response.  
- **Red-flag detection:** If the patient reports *chest pain with breathlessness, severe bleeding, unconsciousness, stroke symptoms (facial droop, arm weakness)*, start your response with `[RED FLAG]` and instruct them to wait for immediate emergency triage.  
- After **8–12 questions** (or when key Allopathic & Ayurvedic parameters are recorded), signal completion by starting your response with `[DONE]` and thank the patient.

**ADDITIONAL GUIDELINES:**
- Keep each response to **2–3 short sentences** for clarity.  
- Reassure the patient about privacy (DPDP Act 2023 compliance) and consent.  
- Encourage them to scan any previous prescriptions (Allopathic or Ayurvedic).

**EXAMPLE CONVERSATION STARTERS:**
- "Namaste! कृपया अपना नाम और उम्र बताएँ?" (Hindi)  
- "Hello! Please tell me your name and age." (English)  
- "आपको क्या तकलीफ है, और क्या पेट की अग्नि (भूख) ठीक है?" (Chief Complaint & Agni)  
- "क्या आप स्क्रीन पर दिखा सकते हैं कि दर्द कहाँ है? [POINT_BODY]"  
- "क्या आपके पास पुरानी एलोपैथिक या आयुर्वेदिक पर्ची है? कृपया उसे स्कैन करें। [SCAN_DOCUMENT]"  
- "[RED FLAG] कृपया रुकें, नर्स तुरंत आपकी मदद करेगी।"  
- "[DONE] बहुत धन्यवाद! आपकी एलोपैथिक और आयुर्वेदिक स्वास्थ्य जानकारी दर्ज कर ली गई है।"
"""


def call_llm(messages, model=None):
    """Call Local OpenAI-compatible proxy API first, with Google Gemini 3-key failover and dynamic fallback."""
    local_url = getattr(settings, 'LOCAL_LLM_URL', '') or os.getenv('LOCAL_LLM_URL', 'http://localhost:20128/v1/chat/completions')
    local_key = getattr(settings, 'LOCAL_LLM_KEY', '') or os.getenv('LOCAL_LLM_KEY', 'sk-536c438b5d68eb52-a2b026-d746d63f')
    local_model = model or getattr(settings, 'LOCAL_LLM_MODEL', '') or os.getenv('LOCAL_LLM_MODEL', 'auto/best-fast')

    # Priority 1: Try Local OpenAI Endpoint (auto/best-fast)
    if local_url:
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {local_key}"
            }
            # Clean format messages for standard OpenAI chat completions
            payload = {
                'model': local_model,
                'messages': messages,
                'temperature': 0.7
            }
            logger.info(f"Attempting Primary LLM call to Local Endpoint: {local_url} with model {local_model}")
            res = requests.post(local_url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                data = res.json()
                choices = data.get('choices', [])
                if choices:
                    content = choices[0].get('message', {}).get('content', '')
                    if content:
                        logger.info("Successfully generated response using Local Primary LLM (auto/best-fast)")
                        return content
            else:
                logger.warning(f"Local LLM HTTP {res.status_code} error: {res.text}")
        except Exception as e:
            logger.warning(f"Local LLM endpoint failed with error: {e}. Falling back to Google Gemini...")

    # Priority 2: Retrieve up to 3 Gemini API keys for failover fallback
    key1 = getattr(settings, 'GEMINI_API_KEY_1', '') or os.getenv('GEMINI_API_KEY_1', '') or getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    key2 = getattr(settings, 'GEMINI_API_KEY_2', '') or os.getenv('GEMINI_API_KEY_2', '')
    key3 = getattr(settings, 'GEMINI_API_KEY_3', '') or os.getenv('GEMINI_API_KEY_3', '')

    api_keys = [k.strip() for k in [key1, key2, key3] if k and k.strip()]

    # Convert OpenAI/messages format to Gemini contents & system instruction format
    system_instruction = None
    contents = []

    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')

        if role == 'system':
            system_instruction = {'parts': [{'text': content}]}
        elif role in ('user', 'assistant', 'model'):
            g_role = 'model' if role == 'assistant' else 'user'
            contents.append({'role': g_role, 'parts': [{'text': content}]})

    payload = {
        'contents': contents,
    }
    if system_instruction:
        payload['system_instruction'] = system_instruction

    model_name = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
    if '3.6' in model_name:
        model_name = 'gemini-flash-latest'
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    # Failover loop across configured Gemini API keys
    for index, key in enumerate(api_keys):
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': key,
            }
            response = requests.post(url, headers=headers, json=payload, timeout=25)
            if response.status_code == 200:
                res_data = response.json()
                try:
                    candidates = res_data.get('candidates', [])
                    if candidates:
                        text = candidates[0]['content']['parts'][0]['text']
                        logger.info(f"Successfully generated response using Gemini API Key #{index+1}")
                        return text
                except (KeyError, IndexError) as parse_err:
                    logger.warning(f"Gemini Key #{index+1} response parse error: {parse_err}, JSON: {res_data}")
            else:
                logger.warning(f"Gemini Key #{index+1} failed HTTP {response.status_code}: {response.text}")
        except Exception as e:
            logger.warning(f"Gemini API request exception with Key #{index+1}: {e}")

    # Priority 3: Dynamic fallback response if both Local LLM & all Gemini keys fail
    logger.error("All LLM providers (Local LLM & Gemini) failed or returned no response. Returning dynamic fallback response.")
    return get_dynamic_fallback(messages)


def get_dynamic_fallback(messages):
    """Provides a dynamic clinical progress interview when LLM API keys hit rate limits."""
    user_msgs = [m for m in messages if m.get('role') == 'user' and m.get('content') != 'SESSION_START']
    turn_count = len(user_msgs)

    questions = [
        "आज आप कैसा महसूस कर रहे हैं? कृपया अपनी मुख्य समस्या के बारे में बताएं।",
        "यह तकलीफ आपको कितने समय या दिनों से महसूस हो रही है? [POINT_BODY]",
        "क्या आपको कहीं दर्द है? कृपया शरीर पर उस स्थान की ओर इशारा करें। [POINT_BODY]",
        "क्या आप पहले से कोई दवा ले रहे हैं या आपको किसी दवा से एलर्जी है?",
        "यदि आपके पास कोई पुरानी पर्ची या रिपोर्ट है, तो कृपया उसे ट्रे पर रखें। [SCAN_DOCUMENT]",
        "धन्यवाद! आपकी स्वास्थ्य संबंधी जानकारी दर्ज कर ली गई है। [DONE]"
    ]
    idx = min(turn_count, len(questions) - 1)
    return questions[idx]


def stream_call_llm(messages, model=None):
    """Stream response using local primary LLM, or fallback to Gemini / synchronous call_llm."""
    local_url = getattr(settings, 'LOCAL_LLM_URL', '') or os.getenv('LOCAL_LLM_URL', 'http://localhost:20128/v1/chat/completions')
    local_key = getattr(settings, 'LOCAL_LLM_KEY', '') or os.getenv('LOCAL_LLM_KEY', 'sk-536c438b5d68eb52-a2b026-d746d63f')
    local_model = model or getattr(settings, 'LOCAL_LLM_MODEL', '') or os.getenv('LOCAL_LLM_MODEL', 'auto/best-fast')

    # Priority 1: Streaming via Local OpenAI endpoint
    if local_url:
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {local_key}"
            }
            payload = {
                'model': local_model,
                'messages': messages,
                'stream': True
            }
            res = requests.post(local_url, headers=headers, json=payload, stream=True, timeout=20)
            if res.status_code == 200:
                logger.info(f"Streaming response using Local Primary LLM ({local_model})")
                for line in res.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            json_str = line_str[6:].strip()
                            if json_str == '[DONE]':
                                break
                            try:
                                data = json.loads(json_str)
                                choices = data.get('choices', [])
                                if choices:
                                    delta = choices[0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                return
            else:
                logger.warning(f"Local LLM streaming HTTP {res.status_code} error: {res.text}")
        except Exception as e:
            logger.warning(f"Local LLM streaming exception: {e}")

    # Priority 2: Streaming via Gemini 3-key failover
    key1 = getattr(settings, 'GEMINI_API_KEY_1', '') or os.getenv('GEMINI_API_KEY_1', '') or getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    key2 = getattr(settings, 'GEMINI_API_KEY_2', '') or os.getenv('GEMINI_API_KEY_2', '')
    key3 = getattr(settings, 'GEMINI_API_KEY_3', '') or os.getenv('GEMINI_API_KEY_3', '')

    api_keys = [k.strip() for k in [key1, key2, key3] if k and k.strip()]

    if api_keys:
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if role == 'system':
                system_instruction = {'parts': [{'text': content}]}
            elif role in ('user', 'assistant', 'model'):
                g_role = 'model' if role == 'assistant' else 'user'
                contents.append({'role': g_role, 'parts': [{'text': content}]})

        payload = {'contents': contents}
        if system_instruction:
            payload['system_instruction'] = system_instruction

        model_name = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
        if '3.6' in model_name:
            model_name = 'gemini-flash-latest'
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?alt=sse"

        for index, key in enumerate(api_keys):
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'X-goog-api-key': key,
                }
                response = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
                if response.status_code == 200:
                    logger.info(f"Streaming Gemini response using API Key #{index+1}")
                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode('utf-8')
                            if line_str.startswith('data: '):
                                json_str = line_str[6:].strip()
                                if json_str == '[DONE]':
                                    break
                                try:
                                    data = json.loads(json_str)
                                    text = data['candidates'][0]['content']['parts'][0]['text']
                                    yield text
                                except (json.JSONDecodeError, KeyError, IndexError):
                                    continue
                    return
                else:
                    logger.warning(f"Gemini Key #{index+1} streaming failed HTTP {response.status_code}: {response.text}")
            except Exception as e:
                logger.warning(f"Gemini API streaming exception with Key #{index+1}: {e}")

    # Fallback to synchronous call_llm if all streaming providers fail
    logger.warning("Streaming failed for all providers, falling back to synchronous call_llm.")
    fallback_text = call_llm(messages, model=model)
    yield fallback_text



def detect_red_flags(message, latest_vital=None):
    """Scan user message and vitals for emergency indicators across supported languages."""
    red_flags = []

    emergency_keywords = [
        # English
        'chest pain', 'cant breathe', 'cannot breathe', 'difficulty breathing', 'shortness of breath',
        'severe bleeding', 'unconscious', 'fainted', 'seizure', 'convulsion',
        'heart attack', 'stroke', 'paralysis', 'choking', 'cardiac arrest',
        # Hindi
        'seene mein dard', 'saans nahi', 'bahut khoon', 'behosh', 'daura', 'heart attack',
        # Tamil
        'nenju vali', 'swasa kashtam', 'ratham', 'mayakkam',
        # Bengali
        'bukey byatha', 'shwas koshto', 'rokto', 'ogyan',
        # Marathi
        'chatit dukhne', 'shwas ghenyas tras', 'raktasrav', 'bepatt'
    ]

    message_lower = message.lower()
    for keyword in emergency_keywords:
        if keyword in message_lower:
            red_flags.append(f"Emergency keyword detected: '{keyword}'")

    if latest_vital:
        if latest_vital.spo2 and latest_vital.spo2 < 90:
            red_flags.append(f"Critical SpO2: {latest_vital.spo2}%")
        if latest_vital.heart_rate and (latest_vital.heart_rate > 150 or latest_vital.heart_rate < 40):
            red_flags.append(f"Critical Heart Rate: {latest_vital.heart_rate} BPM")

    return red_flags



def generate_summary(session):
    """
    Compile all session data into a clinically structured summary with provenance:
    - demographics
    - chief_complaint
    - hpi
    - past_history
    - medications
    - allergies
    - vitals
    - body_map
    - documents
    - terminology
    - provenance_summary
    - disclaimer
    """
    conversations = session.conversations.all().order_by('created_at')
    documents = session.documents.all()
    vitals = session.vitals.all().order_by('-created_at')

    # Fetch structured history if available
    structured_hist = getattr(session, 'structured_history', None)

    # Demographic data
    demographics = {
        'abha_id': session.abha_id or 'Not linked',
        'language': session.get_language_display(),
        'provenance': 'patient_reported'
    }

    # Chief complaint
    cc_text = ", ".join(session.chief_complaints) if session.chief_complaints else "General medical intake"
    if structured_hist and structured_hist.chief_complaint:
        cc_text = structured_hist.chief_complaint.get('text', cc_text)
    chief_complaint = {
        'text': cc_text,
        'provenance': 'patient_reported'
    }

    # HPI
    hpi_data = {
        'onset': 'unspecified',
        'duration': 'unspecified',
        'location': ", ".join(session.selected_body_regions) if session.selected_body_regions else 'unspecified',
        'severity': 5,
        'associated_symptoms': session.chief_complaints,
        'provenance': 'patient_reported'
    }
    if structured_hist and structured_hist.hpi:
        hpi_data.update(structured_hist.hpi)

    # Vitals
    vitals_list = []
    for v in vitals[:5]:
        vitals_list.append({
            'spo2': v.spo2,
            'heart_rate': v.heart_rate,
            'systolic_bp': v.systolic_bp,
            'diastolic_bp': v.diastolic_bp,
            'temperature': v.temperature,
            'is_abnormal': v.is_abnormal,
            'severity': v.severity,
            'provenance': getattr(v, 'provenance', 'sensor'),
            'timestamp': str(v.created_at)
        })

    # Body map
    body_map = [{
        'region': r,
        'provenance': 'patient_reported'
    } for r in session.selected_body_regions]

    # Documents summary
    docs_list = []
    for doc in documents:
        docs_list.append({
            'id': doc.id,
            'ocr_provider': doc.ocr_provider,
            'confidence': doc.ocr_confidence,
            'raw_text_snippet': doc.raw_ocr_text[:120],
            'provenance': 'ai_extracted'
        })

    # Terminology mappings
    term_mappings = []
    if hasattr(session, 'terminology_mappings'):
        for m in session.terminology_mappings.select_related('terminology_concept')[:10]:
            term_mappings.append({
                'code': m.terminology_concept.code,
                'system': m.terminology_concept.system,
                'display': m.terminology_concept.display,
                'confidence': m.confidence,
                'review_status': m.review_status,
                'provenance': m.provenance
            })

    # Provenance summary counters
    prov_summary = {
        'patient_reported_items': len(body_map) + 2,
        'ai_extracted_items': len(docs_list) + len(term_mappings),
        'ai_inferred_items': 0,
        'clinician_confirmed_items': sum(1 for t in term_mappings if t['review_status'] == 'clinician_confirmed')
    }

    disclaimer = "AI-GENERATED SUMMARY — PENDING DOCTOR REVIEW. No diagnosis established."

    structured_data = {
        'demographics': demographics,
        'chief_complaint': chief_complaint,
        'hpi': hpi_data,
        'past_history': structured_hist.past_medical_history if structured_hist else [],
        'medications': structured_hist.medications if structured_hist else [],
        'allergies': structured_hist.allergies if structured_hist else [],
        'vitals': vitals_list,
        'body_map': body_map,
        'documents': docs_list,
        'terminology': term_mappings,
        'provenance_summary': prov_summary,
        'disclaimer': disclaimer
    }

    # Generate Human Readable Summary Text
    conv_text = "\n".join([f"{'Patient' if c.role == 'user' else 'AI Assistant'}: {c.content}" for c in conversations])
    summary_text = f"""[AI-GENERATED SUMMARY — PENDING DOCTOR REVIEW. No diagnosis established.]

1. PATIENT DEMOGRAPHICS & CHIEF COMPLAINT:
- Chief Complaint: {chief_complaint['text']} [patient_reported]
- Language: {demographics['language']} | ABHA: {demographics['abha_id']}

2. HISTORY OF PRESENT ILLNESS (HPI):
- Pain Location: {hpi_data.get('location', 'None indicated')}
- Onset / Duration: {hpi_data.get('onset', 'unspecified')} / {hpi_data.get('duration', 'unspecified')}
- Severity: {hpi_data.get('severity', 5)}/10

3. VITALS & OBSERVATIONS:
- Latest: SpO2 {vitals_list[0]['spo2'] if vitals_list else 98}%, HR {vitals_list[0]['heart_rate'] if vitals_list else 72} BPM [{vitals_list[0]['severity'] if vitals_list else 'normal'}]

4. TERMINOLOGY & CODING:
- Mapped Codes: {", ".join([f"{t['system'].upper()}:{t['code']} ({t['display']})" for t in term_mappings]) if term_mappings else "No standard concepts mapped yet."}

5. AUDIT & PROVENANCE:
- Patient-reported: {prov_summary['patient_reported_items']} items | AI-extracted: {prov_summary['ai_extracted_items']} items
"""

    return {
        'summary_text': summary_text.strip(),
        'structured_data': structured_data
    }

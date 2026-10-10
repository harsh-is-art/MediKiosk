/* =============================================================================
   MediKiosk SPA — app.js
   Complete client-side logic for the kiosk patient intake flow.
   ============================================================================= */

// =============================================================================
// State Management
// =============================================================================
const AppState = {
    currentScreen: 'screen-welcome',
    screenHistory: [],
    language: null,
    sessionId: null,
    tokenNumber: null,
    selectedSymptoms: [],
    selectedBodyRegions: [],
    conversationLength: 0,
    vitalsInterval: null,
    inactivityTimer: null,
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    ttsEnabled: true,
};

// Screen flow order
const SCREEN_ORDER = [
    'screen-welcome',
    'screen-consent',
    // screen-symptoms skipped — body tracking handled by Gemini [POINT_BODY] trigger
    'screen-chat',
    'screen-scan',
    'screen-vitals',
    'screen-completion',
];

// =============================================================================
// Internationalization
// =============================================================================
const I18N = {
    en: {
        welcomeTitle: 'Please choose your language',
        consentTitle: 'We will ask you about your health.',
        consentSubtitle: 'Your information is private and safe.',
        disagree: 'I Do Not Agree',
        agree: 'I Agree',
        symptomTitle: 'Tap where it hurts or select a symptom.',
        chatTitle: 'Tell us more about your health.',
        scanTitle: 'Place your document on the tray',
        scanSubtitle: 'Then tap "Scan Now" to capture the document.',
        scanBtn: 'Scan Now',
        vitalsTitle: 'Please keep your finger on the sensor.',
        vitalsSubtitle: 'Do not move your hand while reading is in progress.',
        summaryHeading: 'Your Medical Summary',
        completionMsg: 'All done! Thank you.',
        back: 'Back',
        next: 'Next',
        fever: 'Fever', cough: 'Cough', pain: 'Pain',
        headache: 'Headache', nausea: 'Nausea', other: 'Other',
        alertText: 'Please wait, a nurse is coming.',
    },
    hi: {
        welcomeTitle: 'कृपया अपनी भाषा चुनें',
        consentTitle: 'हम आपसे आपके स्वास्थ्य के बारे में पूछेंगे।',
        consentSubtitle: 'आपकी जानकारी निजी और सुरक्षित है।',
        disagree: 'मैं सहमत नहीं',
        agree: 'मैं सहमत हूँ',
        symptomTitle: 'जहाँ दर्द हो वहाँ टैप करें या लक्षण चुनें।',
        chatTitle: 'अपने स्वास्थ्य के बारे में और बताएं।',
        scanTitle: 'अपना दस्तावेज़ ट्रे पर रखें',
        scanSubtitle: 'फिर "स्कैन करें" पर टैप करें।',
        scanBtn: 'स्कैन करें',
        vitalsTitle: 'कृपया अपनी उंगली सेंसर पर रखें।',
        vitalsSubtitle: 'रीडिंग के दौरान अपना हाथ न हिलाएं।',
        summaryHeading: 'आपका चिकित्सा सारांश',
        completionMsg: 'पूरा हो गया! धन्यवाद।',
        back: 'पीछे',
        next: 'आगे',
        fever: 'बुखार', cough: 'खांसी', pain: 'दर्द',
        headache: 'सिरदर्द', nausea: 'मतली', other: 'अन्य',
        alertText: 'कृपया प्रतीक्षा करें, नर्स आ रही हैं।',
    },
    ta: {
        welcomeTitle: 'உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்',
        consentTitle: 'உங்கள் உடல்நலம் பற்றி கேட்போம்.',
        consentSubtitle: 'உங்கள் தகவல் தனிப்பட்டது மற்றும் பாதுகாப்பானது.',
        disagree: 'ஒப்புக்கொள்ளவில்லை',
        agree: 'ஒப்புக்கொள்கிறேன்',
        symptomTitle: 'வலிக்கும் இடத்தைத் தொடவும் அல்லது அறிகுறியைத் தேர்ந்தெடுக்கவும்.',
        chatTitle: 'உங்கள் உடல்நலம் பற்றி மேலும் கூறுங்கள்.',
        scanTitle: 'உங்கள் ஆவணத்தை வைக்கவும்',
        scanSubtitle: '"ஸ்கேன்" என்பதைத் தொடவும்.',
        scanBtn: 'ஸ்கேன்',
        vitalsTitle: 'உங்கள் விரலை சென்சாரில் வைக்கவும்.',
        vitalsSubtitle: 'படிக்கும்போது உங்கள் கையை நகர்த்தாதீர்கள்.',
        summaryHeading: 'உங்கள் மருத்துவ சுருக்கம்',
        completionMsg: 'முடிந்தது! நன்றி.',
        back: 'பின்',
        next: 'அடுத்து',
        fever: 'காய்ச்சல்', cough: 'இருமல்', pain: 'வலி',
        headache: 'தலைவலி', nausea: 'குமட்டல்', other: 'மற்றவை',
        alertText: 'காத்திருங்கள், நர்ஸ் வருகிறார்.',
    },
    bn: {
        welcomeTitle: 'আপনার ভাষা বেছে নিন',
        consentTitle: 'আমরা আপনার স্বাস্থ্য সম্পর্কে জিজ্ঞাসা করব।',
        consentSubtitle: 'আপনার তথ্য ব্যক্তিগত এবং নিরাপদ।',
        disagree: 'আমি রাজি নই',
        agree: 'আমি রাজি',
        symptomTitle: 'ব্যথার জায়গায় টাচ করুন বা লক্ষণ বাছুন।',
        chatTitle: 'আপনার স্বাস্থ্য সম্পর্কে আরও বলুন।',
        scanTitle: 'আপনার নথি ট্রেতে রাখুন',
        scanSubtitle: 'তারপর "স্ক্যান" এ টাচ করুন।',
        scanBtn: 'স্ক্যান',
        vitalsTitle: 'আপনার আঙুল সেন্সরে রাখুন।',
        vitalsSubtitle: 'রিডিং চলাকালীন হাত নাড়াবেন না।',
        summaryHeading: 'আপনার চিকিৎসা সারাংশ',
        completionMsg: 'সব হয়ে গেছে! ধন্যবাদ।',
        back: 'পিছনে',
        next: 'পরবর্তী',
        fever: 'জ্বর', cough: 'কাশি', pain: 'ব্যথা',
        headache: 'মাথাব্যথা', nausea: 'বমি বমি', other: 'অন্যান্য',
        alertText: 'অনুগ্রহ করে অপেক্ষা করুন, নার্স আসছেন।',
    },
    mr: {
        welcomeTitle: 'कृपया तुमची भाषा निवडा',
        consentTitle: 'आम्ही तुम्हाला तुमच्या आरोग्याबद्दल विचारू.',
        consentSubtitle: 'तुमची माहिती खाजगी आणि सुरक्षित आहे.',
        disagree: 'मी सहमत नाही',
        agree: 'मी सहमत आहे',
        symptomTitle: 'जिथे दुखत आहे तिथे टॅप करा किंवा लक्षण निवडा.',
        chatTitle: 'तुमच्या आरोग्याबद्दल अधिक सांगा.',
        scanTitle: 'तुमचा कागद ट्रेवर ठेवा',
        scanSubtitle: '"स्कॅन करा" वर टॅप करा.',
        scanBtn: 'स्कॅन करा',
        vitalsTitle: 'कृपया तुमचे बोट सेन्सरवर ठेवा.',
        vitalsSubtitle: 'रीडिंग होत असताना हात हलवू नका.',
        summaryHeading: 'तुमचा वैद्यकीय सारांश',
        completionMsg: 'पूर्ण झाले! धन्यवाद.',
        back: 'मागे',
        next: 'पुढे',
        fever: 'ताप', cough: 'खोकला', pain: 'वेदना',
        headache: 'डोकेदुखी', nausea: 'मळमळ', other: 'इतर',
        alertText: 'कृपया थांबा, नर्स येत आहे.',
    },
};

function t(key) {
    const lang = AppState.language || 'en';
    return (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
}

function updateUILanguage() {
    const lang = AppState.language || 'en';

    // Update all translatable elements
    const el = (id) => document.getElementById(id);

    if (el('consent-title')) el('consent-title').textContent = t('consentTitle');
    if (el('consent-subtitle')) el('consent-subtitle').textContent = t('consentSubtitle');
    if (el('btn-disagree-text')) el('btn-disagree-text').textContent = t('disagree');
    if (el('btn-agree-text')) el('btn-agree-text').textContent = t('agree');
    if (el('symptom-title')) el('symptom-title').textContent = t('symptomTitle');
    if (el('chat-title')) el('chat-title').textContent = t('chatTitle');
    if (el('scan-title')) el('scan-title').textContent = t('scanTitle');
    if (el('scan-subtitle')) el('scan-subtitle').textContent = t('scanSubtitle');
    if (el('scan-btn-text')) el('scan-btn-text').textContent = t('scanBtn');
    if (el('vitals-title')) el('vitals-title').textContent = t('vitalsTitle');
    if (el('vitals-subtitle')) el('vitals-subtitle').textContent = t('vitalsSubtitle');
    if (el('summary-heading')) el('summary-heading').textContent = t('summaryHeading');
    if (el('completion-message')) el('completion-message').textContent = t('completionMsg');
    if (el('btn-back-text')) el('btn-back-text').textContent = t('back');
    if (el('btn-next-text')) el('btn-next-text').textContent = t('next');
    if (el('alert-text')) el('alert-text').textContent = t('alertText');

    // Update symptom card labels
    document.querySelectorAll('.symptom-card').forEach(card => {
        const symptom = card.dataset.symptom;
        const label = card.querySelector('.symptom-label');
        if (label && symptom) {
            label.textContent = t(symptom);
        }
    });
}

// =============================================================================
// Screen Navigation
// =============================================================================
function showScreen(screenId) {
    const current = document.getElementById(AppState.currentScreen);
    const next = document.getElementById(screenId);

    if (!next) return;

    // Add current to history
    if (AppState.currentScreen !== screenId) {
        AppState.screenHistory.push(AppState.currentScreen);
    }

    // Animate out current
    if (current) {
        current.classList.remove('active');
        current.classList.add('exit-left');
    }

    // Animate in next
    next.classList.remove('exit-left');

    // Force reflow
    void next.offsetWidth;

    next.classList.add('active');
    AppState.currentScreen = screenId;

    // Trigger or stop live OCR camera stream
    if (screenId === 'screen-scan') {
        startOcrCameraStream();
    } else {
        stopOcrCameraStream();
    }

    // Update nav visibility
    updateNavigation();

    // Speak screen content
    if (AppState.ttsEnabled) {
        speakScreenContent(screenId);
    }

    // Reset inactivity timer
    resetInactivityTimer();
}

function goBack() {
    if (AppState.screenHistory.length > 0) {
        const prev = AppState.screenHistory.pop();
        const current = document.getElementById(AppState.currentScreen);
        const prevEl = document.getElementById(prev);

        if (current) {
            current.classList.remove('active');
        }
        if (prevEl) {
            prevEl.classList.remove('exit-left');
            prevEl.classList.add('active');
        }

        AppState.currentScreen = prev;
        updateNavigation();
    }
}

function goNext() {
    const currentIdx = SCREEN_ORDER.indexOf(AppState.currentScreen);
    if (currentIdx < SCREEN_ORDER.length - 1) {
        const nextScreen = SCREEN_ORDER[currentIdx + 1];

        // Special actions before transitioning
        if (AppState.currentScreen === 'screen-symptoms') {
            submitSymptoms();
            return; // submitSymptoms handles the transition
        }

        if (nextScreen === 'screen-vitals') {
            startVitalsPolling();
        }

        if (nextScreen === 'screen-completion') {
            generateSummary();
        }

        showScreen(nextScreen);
    }
}

function setVoiceStatus(text, state) {
    const pill = document.getElementById('voice-status-pill');
    const icon = document.getElementById('voice-status-icon');
    const txt = document.getElementById('voice-status-text');
    if (!pill || !txt) return;

    txt.textContent = text;
    pill.className = 'voice-status-pill ' + (state || '');
    if (icon) {
        if (state === 'speaking') icon.textContent = 'volume_up';
        else if (state === 'listening') icon.textContent = 'graphic_eq';
        else icon.textContent = 'mic';
    }
}

function unlockAudioAndStart() {
    const splash = document.getElementById('audio-splash-overlay');
    if (splash) {
        splash.classList.add('hidden');
    }
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
            const ctx = new AudioCtx();
            if (ctx.state === 'suspended') ctx.resume();
        }
    } catch (e) {}

    setVoiceStatus('Welcome Greeting...', 'speaking');
    speakScreenContent('screen-welcome');
}

function updateNavigation() {
    const bottomNav = document.getElementById('bottom-nav');
    const startBtnContainer = document.getElementById('start-btn-container');
    const btnBack = document.getElementById('btn-back');
    const btnNext = document.getElementById('btn-next');

    // Stepper dots progress mapping
    const screenStepMap = {
        'screen-welcome': 1,
        'screen-consent': 2,
        'screen-chat': 3,
        'screen-scan': 4,
        'screen-vitals': 5,
        'screen-completion': 5
    };
    const currentStep = screenStepMap[AppState.currentScreen] || 1;

    for (let i = 1; i <= 5; i++) {
        const dot = document.getElementById(`step-dot-${i}`);
        if (dot) {
            dot.classList.remove('active', 'completed');
            if (i < currentStep) dot.classList.add('completed');
            else if (i === currentStep) dot.classList.add('active');
        }
    }

    // Hide bottom nav on welcome and completion screens
    const hideNavScreens = ['screen-welcome', 'screen-consent', 'screen-completion'];
    if (bottomNav) {
        bottomNav.classList.toggle('hidden', hideNavScreens.includes(AppState.currentScreen));
    }

    // Disable back button when no screen history
    if (btnBack) {
        btnBack.classList.toggle('btn-disabled', AppState.screenHistory.length === 0);
    }

    // Update next button text for vitals screen
    if (btnNext && AppState.currentScreen === 'screen-vitals') {
        const nextText = document.getElementById('btn-next-text');
        if (nextText) nextText.textContent = 'Finish';
    }
}

// =============================================================================
// Screen 1: Language Selection
// =============================================================================
function selectLanguage(lang, el) {
    AppState.language = lang;

    // Clear all selections
    document.querySelectorAll('.language-card').forEach(card => {
        card.classList.remove('card-selected');
    });

    // Select this card
    el.classList.add('card-selected');

    // Enable start button
    const startBtn = document.getElementById('btn-start');
    startBtn.disabled = false;
    startBtn.classList.add('animate-pulse');
    setTimeout(() => startBtn.classList.remove('animate-pulse'), 1000);

    // Update UI language
    updateUILanguage();
}

function goToConsent() {
    if (!AppState.language) return;
    showScreen('screen-consent');
}

// =============================================================================
// Screen 2: Consent
// =============================================================================
function handleConsent(agreed) {
    if (agreed) {
        // Proceed to ABHA Registration Screen
        showScreen('screen-abha');
    } else {
        startOver();
    }
}

function selectAbhaValidation(type) {
    document.querySelectorAll('.abha-validate-card').forEach(c => c.classList.remove('active'));
    if (type === 'aadhaar') {
        const el = document.getElementById('val-aadhaar');
        if (el) el.classList.add('active');
    } else {
        const el = document.getElementById('val-mobile');
        if (el) el.classList.add('active');
    }
}

function submitAbhaRegistration() {
    const inputVal = document.getElementById('abha-input').value.trim();
    if (inputVal) {
        AppState.abhaId = inputVal;
    }
    // Transition to ABHA Address Login Screen
    showScreen('screen-abha-login');
}

function openAbhaLoginModal() {
    showScreen('screen-abha-login');
}

function completeAbhaLogin() {
    const selectedRadio = document.querySelector('input[name="abha_address"]:checked');
    if (selectedRadio) {
        AppState.abhaAddress = selectedRadio.value;
    }
    // Proceed to create session & start AI interview
    createSession();
}

async function createSession() {
    try {
        const resp = await fetch('/api/session/start/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                language: AppState.language,
                consent: true,
            }),
        });

        if (resp.ok) {
            const data = await resp.json();
            AppState.sessionId = data.id;
            AppState.tokenNumber = data.token_number;
        }
    } catch (e) {
        console.error('Session creation error:', e);
        AppState.sessionId = 'demo-' + Date.now();
        AppState.tokenNumber = Math.floor(Math.random() * 900) + 100;
    }

    showScreen('screen-chat');
    startGeminiInterview();
}

/**
 * Kick off the Gemini interview with an opening greeting.
 * Gemini will ask questions, trigger [POINT_BODY] for camera tracking,
 * and [SCAN_DOCUMENT] for OCR — all without any touch from the user.
 */
async function startGeminiInterview() {
    const lang = AppState.language || 'hi';
    const openingMsg = lang === 'hi'
        ? 'नमस्ते! आज आप कैसा महसूस कर रहे हैं? कृपया बताएं।'
        : 'Hello! How are you feeling today? Please tell me what brought you in.';

    // Show opening bubble and speak opening question aloud (triggers auto-mic when speech finishes)
    addChatBubble('assistant', openingMsg);
    speak(openingMsg, true, lang);

    // Stream system prompt to Gemini for clinical evaluation
    try {
        await streamChatMessage('SESSION_START', 'system');
    } catch (e) {
        console.error('Gemini interview start error:', e);
    }
}

// =============================================================================
// Screen 3: Symptoms
// =============================================================================
function toggleSymptom(symptom, el) {
    const idx = AppState.selectedSymptoms.indexOf(symptom);
    if (idx >= 0) {
        AppState.selectedSymptoms.splice(idx, 1);
        el.classList.remove('selected');
    } else {
        AppState.selectedSymptoms.push(symptom);
        el.classList.add('selected');
    }
}

function toggleBodyRegion(region, el) {
    const idx = AppState.selectedBodyRegions.indexOf(region);
    if (idx >= 0) {
        AppState.selectedBodyRegions.splice(idx, 1);
        el.classList.remove('selected');
    } else {
        AppState.selectedBodyRegions.push(region);
        el.classList.add('selected');
    }
}

async function submitSymptoms() {
    if (AppState.selectedSymptoms.length === 0 && AppState.selectedBodyRegions.length === 0) {
        // Allow proceeding with no selection — some users may just want to talk
        showScreen('screen-chat');
        addChatBubble('assistant', t('chatTitle'));
        return;
    }

    try {
        const resp = await fetch('/api/symptoms/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: AppState.sessionId,
                complaints: AppState.selectedSymptoms,
                body_regions: AppState.selectedBodyRegions,
            }),
        });

        if (resp.ok) {
            const data = await resp.json();
            showScreen('screen-chat');
            addChatBubble('assistant', data.question);
        } else {
            showScreen('screen-chat');
            addChatBubble('assistant', 'Can you tell me more about your symptoms?');
        }
    } catch (e) {
        console.error('Symptom submission error:', e);
        showScreen('screen-chat');
        addChatBubble('assistant', 'Can you tell me more about how you are feeling?');
    }
}

// =============================================================================
// Screen 4: Chat
// =============================================================================
function addChatBubble(role, text, speakAloud = true) {
    const container = document.getElementById('chat-container');
    if (!container) return;
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble text-body-lg ${role === 'assistant' ? 'chat-bubble-assistant' : 'chat-bubble-user'}`;
    bubble.textContent = text;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;

    // Read assistant messages aloud if requested
    if (role === 'assistant' && AppState.ttsEnabled && speakAloud) {
        speak(text);
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    streamChatMessage(message, 'text');
}

async function streamChatMessage(message, inputType = 'text') {
    if (!message) return;
    addChatBubble('user', message);

    const container = document.getElementById('chat-container');
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble text-body-lg chat-bubble-assistant';
    bubble.textContent = '';
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;

    let fullText = '';
    let triggerBodyPointingFlag = false;

    try {
        const response = await fetch('/api/chat/stream/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: AppState.sessionId,
                message: message,
                input_type: inputType,
            }),
        });

        if (!response.ok) {
            bubble.textContent = 'Thank you for sharing. Could you tell me more about how you are feeling?';
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        let triggerOcrFlag = false;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed.startsWith('data: ')) {
                    const jsonStr = trimmed.slice(6);
                    try {
                        const parsed = JSON.parse(jsonStr);
                        if (parsed.text) {
                            fullText += parsed.text;
                            const cleanText = fullText.replace('[POINT_BODY]', '').replace('[SCAN_DOCUMENT]', '');
                            bubble.textContent = cleanText;
                            container.scrollTop = container.scrollHeight;
                        }
                        if (parsed.done) {
                            triggerBodyPointingFlag = parsed.trigger_body_pointing;
                            triggerOcrFlag = parsed.trigger_ocr;
                            if (parsed.red_flags && parsed.red_flags.length > 0) {
                                bubble.classList.add('chat-bubble-redflag');
                            }
                        }
                    } catch (e) {
                        console.error('SSE parse error:', e);
                    }
                }
            }
        }

        const finalCleanText = fullText.replace('[POINT_BODY]', '').replace('[SCAN_DOCUMENT]', '').trim();
        bubble.textContent = finalCleanText;

        if (AppState.ttsEnabled && finalCleanText) {
            speak(finalCleanText);
        }

        if (triggerBodyPointingFlag || fullText.includes('[POINT_BODY]')) {
            triggerBodyPointing();
        }

        if (triggerOcrFlag || fullText.includes('[SCAN_DOCUMENT]')) {
            setTimeout(() => {
                showScreen('screen-scan');
                scanDocument();
            }, 1500);
        }

        if (finalCleanText.startsWith('[DONE]')) {
            setTimeout(() => showScreen('screen-scan'), 2000);
        }

    } catch (e) {
        console.error('Stream chat error:', e);
        bubble.textContent = 'Thank you. Could you share more details?';
    }
}

// =============================================================================
// Body Pointing Tracker (Tablet Camera Feed + Backend MediaPipe GPU Processing)
// =============================================================================
let activeCameraStream = null;

async function triggerBodyPointing() {
    const overlay = document.getElementById('camera-tracker-overlay');
    const video = document.getElementById('tablet-camera-video');
    const statusText = document.getElementById('tracker-live-text');

    if (overlay) overlay.style.display = 'flex';
    if (statusText) statusText.textContent = 'Starting camera feed on your device...';

    // 1. Start local camera feed on tablet/browser
    try {
        if (!activeCameraStream) {
            activeCameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
                audio: false
            });
        }
        if (video) {
            video.srcObject = activeCameraStream;
            await video.play();
        }
    } catch (err) {
        console.warn('Local webcam access failed or denied, continuing with server camera/API:', err);
        if (statusText) statusText.textContent = 'Camera active. Analyzing body pointing with GPU server...';
    }

    if (statusText) statusText.textContent = 'Point index finger at symptom area... Running GPU tracker';

    // 2. Call backend MediaPipe tracker endpoint (performs calculation on Nvidia GPU/Server)
    try {
        const resp = await fetch('/api/body-pointing/', { method: 'POST' });
        if (resp.ok) {
            const data = await resp.json();
            if (data.detected_region) {
                if (statusText) statusText.textContent = `Detected Region: ${data.detected_region.toUpperCase()}`;
                addChatBubble('assistant', `I detected point location: ${data.detected_region}.`);
            }
        }
    } catch (err) {
        console.error('Body pointing API error:', err);
    }

    // Automatically hide modal after 4 seconds
    setTimeout(() => {
        closeCameraTracker();
    }, 4000);
}

function closeCameraTracker() {
    const overlay = document.getElementById('camera-tracker-overlay');
    const video = document.getElementById('tablet-camera-video');

    if (overlay) overlay.style.display = 'none';

    if (activeCameraStream) {
        activeCameraStream.getTracks().forEach(track => track.stop());
        activeCameraStream = null;
    }
    if (video) {
        video.srcObject = null;
    }
}



async function sendChatMessageWithText(customText) {
    if (!customText) return;
    streamChatMessage(customText, 'body_pointing');
}

function sendQuickReply(text) {
    document.getElementById('chat-input').value = text;
    sendChatMessage();
}

// =============================================================================
// Screen 5: Document Scanning (Real-time OCR Camera Feed)
// =============================================================================
let activeOcrStream = null;

async function startOcrCameraStream() {
    const video = document.getElementById('ocr-camera-video');
    const placeholder = document.getElementById('ocr-camera-placeholder');

    try {
        if (!activeOcrStream) {
            activeOcrStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false
            });
        }
        if (video) {
            video.srcObject = activeOcrStream;
            video.style.display = 'block';
            if (placeholder) placeholder.style.display = 'none';
            await video.play();
        }
    } catch (err) {
        console.warn('Local camera access for OCR failed/denied, falling back to IP camera placeholder:', err);
        if (placeholder) placeholder.style.display = 'flex';
        if (video) video.style.display = 'none';
    }
}

function stopOcrCameraStream() {
    const video = document.getElementById('ocr-camera-video');
    const placeholder = document.getElementById('ocr-camera-placeholder');

    if (activeOcrStream) {
        activeOcrStream.getTracks().forEach(track => track.stop());
        activeOcrStream = null;
    }
    if (video) {
        video.srcObject = null;
        video.style.display = 'none';
    }
    if (placeholder) {
        placeholder.style.display = 'flex';
    }
}

async function scanDocument() {
    const btn = document.getElementById('btn-scan');
    const resultBox = document.getElementById('ocr-result-box');
    const video = document.getElementById('ocr-camera-video');
    const canvas = document.getElementById('ocr-camera-canvas');

    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Scanning document...';

    try {
        let formData = new FormData();
        formData.append('session_id', AppState.sessionId);

        // If local webcam is running, capture the live frame to send for OCR
        if (video && video.srcObject && canvas && video.videoWidth > 0) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.90));
            if (blob) {
                formData.append('image', blob, 'ocr_snapshot.jpg');
            }
        }

        const resp = await fetch('/api/document/', {
            method: 'POST',
            body: formData,
        });

        if (resp.ok) {
            const data = await resp.json();
            resultBox.style.display = 'block';

            const confPercent = Math.round((data.confidence || 0.90) * 100);

            if (data.status === 'accepted' && data.text) {
                // High confidence (>= 90%)
                resultBox.innerHTML = `
                    <div style="background:var(--primary-container);padding:16px;border-radius:12px;margin-bottom:12px">
                        <h3 class="text-headline-sm" style="color:var(--on-primary);display:flex;align-items:center;gap:8px">
                            <span class="material-symbols-outlined icon-filled">check_circle</span>
                            OCR RESULT (Confidence: ${confPercent}%)
                        </h3>
                    </div>
                    <p class="text-body-md" id="ocr-result-text" style="white-space:pre-wrap">${data.text}</p>
                `;

                btn.innerHTML = '<span class="material-symbols-outlined icon-filled" style="font-size:40px">check_circle</span> Document Accepted';

                // Send extracted text directly back to Gemini LLM stream
                setTimeout(() => {
                    stopOcrCameraStream();
                    showScreen('screen-chat');
                    streamChatMessage(`[DOCUMENT_OCR_RESULT] Extracted prescription text: ${data.text}`, 'document_ocr');
                }, 2500);

            } else {
                // Low confidence (< 90%) -> Manual Review Required
                const croppedImgHtml = data.cropped_image ? `<img src="${data.cropped_image}" alt="Cropped Medical Slip" style="max-width:100%;border-radius:12px;margin-top:12px;border:2px solid var(--error)" />` : '';

                resultBox.innerHTML = `
                    <div style="background:#ffdad6;padding:16px;border-radius:12px;margin-bottom:12px">
                        <h3 class="text-headline-sm" style="color:#b3261e;display:flex;align-items:center;gap:8px">
                            <span class="material-symbols-outlined icon-filled">warning</span>
                            LOW CONFIDENCE (Confidence: ${confPercent}%)
                        </h3>
                        <p class="text-body-sm" style="color:#b3261e;margin-top:4px">Manual verification required. Transcribed text is withheld for safety.</p>
                    </div>
                    ${croppedImgHtml}
                `;

                btn.innerHTML = '<span class="material-symbols-outlined icon-filled" style="font-size:40px">warning</span> Sent for Manual Verification';

                // Notify Gemini LLM directly of manual review state
                setTimeout(() => {
                    stopOcrCameraStream();
                    showScreen('screen-chat');
                    streamChatMessage('[DOCUMENT_OCR_RESULT] Prescription scanned with low confidence. Sent image to doctor for manual verification.', 'document_ocr');
                }, 3000);
            }

        } else {
            btn.innerHTML = '<span class="material-symbols-outlined icon-filled" style="font-size:40px">photo_camera</span> Try Again';
        }
    } catch (e) {
        console.error('Scan error:', e);
        btn.innerHTML = '<span class="material-symbols-outlined icon-filled" style="font-size:40px">photo_camera</span> Scan Now';
    }

    btn.disabled = false;
}

// =============================================================================
// Screen 6: Vitals
// =============================================================================
function startVitalsPolling() {
    if (AppState.vitalsInterval) clearInterval(AppState.vitalsInterval);

    AppState.vitalsInterval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/vitals/latest/${AppState.sessionId}/`);
            if (resp.ok) {
                const data = await resp.json();
                updateVitalsDisplay(data);
            }
        } catch (e) {
            // Generate simulated vitals for demo
            updateVitalsDisplay({
                heart_rate: Math.floor(Math.random() * 40) + 65,
                spo2: Math.floor(Math.random() * 5) + 95,
                is_abnormal: {},
            });
        }
    }, 2000);
}

function updateVitalsDisplay(data) {
    const hrValue = document.getElementById('hr-value');
    const spo2Value = document.getElementById('spo2-value');
    const hrCard = document.getElementById('hr-card');
    const spo2Card = document.getElementById('spo2-card');
    const hrBadge = document.getElementById('hr-badge');
    const spo2Badge = document.getElementById('spo2-badge');
    const alert = document.getElementById('vitals-alert');

    if (data.heart_rate) {
        hrValue.textContent = data.heart_rate;
        hrValue.style.color = '';

        const hrAbnormal = data.is_abnormal && data.is_abnormal.heart_rate;
        hrCard.classList.toggle('abnormal', !!hrAbnormal);

        if (hrAbnormal) {
            hrBadge.className = 'vital-status-badge high';
            hrBadge.innerHTML = '<span class="material-symbols-outlined">warning</span><span>' + (hrAbnormal === 'high' ? 'High' : 'Low') + '</span>';
            hrValue.style.color = 'var(--error)';
        } else {
            hrBadge.className = 'vital-status-badge stable';
            hrBadge.innerHTML = '<span class="material-symbols-outlined icon-filled">check_circle</span><span>Normal</span>';
        }
    }

    if (data.spo2) {
        spo2Value.textContent = data.spo2;

        const spo2Abnormal = data.is_abnormal && data.is_abnormal.spo2;
        spo2Card.classList.toggle('abnormal', !!spo2Abnormal);

        if (spo2Abnormal) {
            spo2Badge.className = 'vital-status-badge low';
            spo2Badge.innerHTML = '<span class="material-symbols-outlined">warning</span><span>Low</span>';
        } else {
            spo2Badge.className = 'vital-status-badge stable';
            spo2Badge.innerHTML = '<span class="material-symbols-outlined icon-filled">check_circle</span><span>Stable</span>';
        }
    }

    // Show alert if any vitals are abnormal
    const hasAbnormal = data.is_abnormal && Object.keys(data.is_abnormal).length > 0;
    alert.classList.toggle('hidden', !hasAbnormal);
}

// =============================================================================
// Screen 7: Completion
// =============================================================================
async function generateSummary() {
    const summaryText = document.getElementById('summary-text');
    const tokenDisplay = document.getElementById('token-display');

    summaryText.textContent = 'Generating your summary...';

    // Stop vitals polling
    if (AppState.vitalsInterval) {
        clearInterval(AppState.vitalsInterval);
    }

    try {
        const resp = await fetch(`/api/summary/${AppState.sessionId}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });

        if (resp.ok) {
            const data = await resp.json();
            summaryText.textContent = data.summary_text;
        } else {
            summaryText.textContent = 'Your symptoms and vitals have been recorded. A doctor will review your case shortly.';
        }
    } catch (e) {
        console.error('Summary error:', e);
        const complaints = AppState.selectedSymptoms.join(', ') || 'General consultation';
        summaryText.textContent = `Patient reports: ${complaints}. Vitals recorded. Ready for doctor consultation.`;
    }

    if (AppState.tokenNumber) {
        tokenDisplay.textContent = `Your token number: ${AppState.tokenNumber}`;
    }

    // Auto-reset after 30 seconds
    setTimeout(() => {
        if (AppState.currentScreen === 'screen-completion') {
            startOver();
        }
    }, 30000);
}

// =============================================================================
// Voice Input (MediaRecorder + ASR)
// =============================================================================
let micAutoStopTimer = null;

async function toggleMic() {
    const micBtn = document.getElementById('btn-mic') || document.getElementById('btn-nav-mic');

    if (micAutoStopTimer) {
        clearTimeout(micAutoStopTimer);
        micAutoStopTimer = null;
    }

    if (AppState.isRecording) {
        // Stop recording
        AppState.isRecording = false;
        setVoiceStatus('Processing Speech...', 'speaking');
        if (AppState.mediaRecorder && AppState.mediaRecorder.state !== 'inactive') {
            AppState.mediaRecorder.stop();
        }
        if (micBtn) micBtn.classList.remove('recording');
    } else {
        // Don't start mic if AI is currently speaking
        if (AppState.isSpeaking) return;

        // Start recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            AppState.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            AppState.audioChunks = [];

            AppState.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) AppState.audioChunks.push(e.data);
            };

            AppState.mediaRecorder.onstop = async () => {
                stream.getTracks().forEach(track => track.stop());
                const blob = new Blob(AppState.audioChunks, { type: 'audio/webm' });
                await transcribeAudio(blob);
            };

            AppState.mediaRecorder.start(250);
            AppState.isRecording = true;
            setVoiceStatus('Listening...', 'listening');
            if (micBtn) micBtn.classList.add('recording');

            // Web Audio API Silence / Voice Activity Detection (VAD) Auto Cutoff
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const source = audioCtx.createMediaStreamSource(stream);
                const analyser = audioCtx.createAnalyser();
                analyser.fftSize = 512;
                source.connect(analyser);

                const dataArray = new Uint8Array(analyser.frequencyBinCount);
                let speechDetected = false;
                let lastSpeechTime = Date.now();

                const checkAudioLevel = () => {
                    if (!AppState.isRecording) {
                        try { audioCtx.close(); } catch(e){}
                        return;
                    }
                    analyser.getByteFrequencyData(dataArray);
                    let sum = 0;
                    for (let i = 0; i < dataArray.length; i++) {
                        sum += dataArray[i];
                    }
                    const average = sum / dataArray.length;

                    // Threshold for speech vs background ambient noise
                    if (average > 12) {
                        speechDetected = true;
                        lastSpeechTime = Date.now();
                    } else if (speechDetected && (Date.now() - lastSpeechTime > 1500)) {
                        // 1.5 seconds of silence after user started speaking -> Auto Cutoff mic
                        console.log('VAD: Silence detected after speech, auto-stopping mic...');
                        try { audioCtx.close(); } catch(e){}
                        if (AppState.isRecording) {
                            toggleMic();
                        }
                        return;
                    }
                    requestAnimationFrame(checkAudioLevel);
                };
                requestAnimationFrame(checkAudioLevel);
            } catch (vadErr) {
                console.warn('VAD AudioContext init skipped:', vadErr);
            }

            // 12-second max auto-stop safety timer (prevents exceeding Sarvam 30s STT limit)
            micAutoStopTimer = setTimeout(() => {
                if (AppState.isRecording) {
                    toggleMic();
                }
            }, 12000);
        } catch (e) {
            console.error('Mic error:', e);
            setVoiceStatus('Mic Unavailable', '');
        }
    }
}

async function transcribeAudio(blob) {
    const formData = new FormData();
    formData.append('audio', blob, 'recording.webm');
    if (AppState.sessionId) formData.append('session_id', AppState.sessionId);
    formData.append('language', AppState.language || 'hi');

    try {
        const resp = await fetch('/api/asr/', {
            method: 'POST',
            body: formData,
        });

        if (resp.ok) {
            const data = await resp.json();
            if (data.text && data.text.trim()) {
                const textLower = data.text.toLowerCase().trim();
                console.log('Voice recognized:', data.text);

                // ── Screen 1: Language Selection & Start ────────────────────
                if (AppState.currentScreen === 'screen-welcome') {
                    let chosenLang = AppState.language || 'hi';
                    if (textLower.includes('english') || textLower.includes('अंग्रेज़ी')) chosenLang = 'en';
                    else if (textLower.includes('tamil') || textLower.includes('तमिल')) chosenLang = 'ta';
                    else if (textLower.includes('bengali') || textLower.includes('बांग्ला')) chosenLang = 'bn';
                    else if (textLower.includes('marathi') || textLower.includes('मराठी')) chosenLang = 'mr';
                    else if (textLower.includes('hindi') || textLower.includes('हिंदी')) chosenLang = 'hi';

                    AppState.language = chosenLang;
                    updateUILanguage();

                    const card = document.querySelector(`.language-card[data-lang="${chosenLang}"]`);
                    if (card) {
                        document.querySelectorAll('.language-card').forEach(c => c.classList.remove('card-selected'));
                        card.classList.add('card-selected');
                    }

                    setTimeout(() => goToConsent(), 500);
                    return;
                }

                // ── Screen 2: Privacy Consent ─────────────────────────────────
                if (AppState.currentScreen === 'screen-consent') {
                    const noWords = ['no', 'nahi', 'nahin', 'नहीं', 'disagree', 'नाहीं', 'na', 'reject'];
                    const isDeclined = noWords.some(w => textLower.includes(w));
                    if (isDeclined) {
                        handleConsent(false);
                    } else {
                        handleConsent(true);
                    }
                    return;
                }

                // ── Screen 3 (Chat): All speech goes directly to Gemini ─────
                if (AppState.currentScreen === 'screen-chat') {
                    const input = document.getElementById('chat-input');
                    if (input) input.value = data.text;
                    sendChatMessage();
                }

            }
        }
    } catch (e) {
        console.error('Transcription error:', e);
    } finally {
        if (!AppState.isRecording && !AppState.isSpeaking) {
            setVoiceStatus('Voice Ready', '');
        }
    }
}

// =============================================================================
// Text-to-Speech
// =============================================================================
let currentAudio = null;

function toggleTTS() {
    AppState.ttsEnabled = !AppState.ttsEnabled;
    const btn = document.getElementById('btn-tts');
    if (btn) {
        const icon = btn.querySelector('.material-symbols-outlined');
        icon.textContent = AppState.ttsEnabled ? 'volume_up' : 'volume_off';
    }
    if (!AppState.ttsEnabled && currentAudio) {
        currentAudio.pause();
        currentAudio = null;
        AppState.isSpeaking = false;
        setVoiceStatus('Voice Ready', '');
    }
}

async function speak(text, autoListenAfter = true, languageOverride = null) {
    if (!AppState.ttsEnabled || !text || !text.trim()) return;

    // Instantly cancel any existing playing audio to prevent overlapping speech
    if (currentAudio) {
        try {
            currentAudio.pause();
            currentAudio.currentTime = 0;
        } catch(e){}
        currentAudio = null;
    }

    const speakLang = languageOverride || AppState.language || 'hi';
    AppState.isSpeaking = true;
    setVoiceStatus('AI Speaking...', 'speaking');

    try {
        const response = await fetch('/api/tts/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text.trim(),
                language: speakLang
            })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.audio_base64) {
                if (currentAudio) {
                    try { currentAudio.pause(); } catch(e){}
                    currentAudio = null;
                }
                currentAudio = new Audio('data:audio/wav;base64,' + data.audio_base64);
                currentAudio.onended = () => {
                    currentAudio = null;
                    AppState.isSpeaking = false;
                    setVoiceStatus('Voice Ready', '');
                    // Auto-listen on interactive screens after TTS finishes
                    const interactiveScreens = ['screen-welcome', 'screen-consent', 'screen-chat'];
                    if (autoListenAfter && interactiveScreens.includes(AppState.currentScreen) && !AppState.isRecording) {
                        setTimeout(() => {
                            if (!AppState.isRecording && !AppState.isSpeaking) {
                                toggleMic();
                            }
                        }, 500);
                    }
                };
                currentAudio.play().catch(e => {
                    AppState.isSpeaking = false;
                    setVoiceStatus('Voice Ready', '');
                });
            } else {
                AppState.isSpeaking = false;
                setVoiceStatus('Voice Ready', '');
            }
        } else {
            AppState.isSpeaking = false;
            setVoiceStatus('Voice Ready', '');
        }
    } catch (e) {
        console.error('Chatterbox/Sarvam TTS call failed:', e);
        AppState.isSpeaking = false;
        setVoiceStatus('Voice Ready', '');
    }
}

function speakScreenContent(screenId) {
    const lang = screenId === 'screen-welcome' ? 'hi' : (AppState.language || 'hi');
    const screenTexts = {
        'screen-welcome': 'नमस्ते! मेडिकियोस्क में आपका स्वागत है। कृपया अपनी भाषा चुनें — हिंदी, इंग्लिश, तमिल, बांग्ला, या मराठी।',
        'screen-consent': lang === 'hi' ? 'हम आपके स्वास्थ्य के बारे में पूछेंगे। क्या आप सहमत हैं?' : t('consentTitle'),
        // screen-symptoms removed — body tracking handled by Gemini [POINT_BODY] trigger
        'screen-chat': '',   // Chat questions are spoken by Gemini/Chatterbox when LLM replies
        'screen-vitals': t('vitalsTitle'),
        'screen-completion': t('completionMsg'),
    };

    const text = screenTexts[screenId];
    if (text) {
        speak(text, true, lang);
    }
}


// =============================================================================
// Utility
// =============================================================================
function startOver() {
    // Clear state
    AppState.language = null;
    AppState.sessionId = null;
    AppState.tokenNumber = null;
    AppState.selectedSymptoms = [];
    AppState.selectedBodyRegions = [];
    AppState.conversationLength = 0;
    AppState.screenHistory = [];
    AppState.isRecording = false;

    if (AppState.vitalsInterval) clearInterval(AppState.vitalsInterval);
    if (AppState.inactivityTimer) clearTimeout(AppState.inactivityTimer);

    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    // Reset UI
    document.querySelectorAll('.language-card').forEach(c => c.classList.remove('card-selected'));
    document.querySelectorAll('.symptom-card').forEach(c => c.classList.remove('selected'));
    document.querySelectorAll('.body-region').forEach(c => c.classList.remove('selected'));

    const startBtn = document.getElementById('btn-start');
    if (startBtn) startBtn.disabled = true;

    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) chatContainer.innerHTML = '';

    const ocrBox = document.getElementById('ocr-result-box');
    if (ocrBox) ocrBox.style.display = 'none';

    document.getElementById('hr-value').textContent = '--';
    document.getElementById('spo2-value').textContent = '--';

    // Reset scan button
    const scanBtn = document.getElementById('btn-scan');
    if (scanBtn) {
        scanBtn.innerHTML = '<span class="material-symbols-outlined icon-filled" style="font-size:40px">photo_camera</span><span>Scan Now</span>';
        scanBtn.style.background = '';
    }

    // Navigate to welcome
    document.querySelectorAll('.screen').forEach(s => {
        s.classList.remove('active', 'exit-left');
    });
    document.getElementById('screen-welcome').classList.add('active');
    AppState.currentScreen = 'screen-welcome';
    updateNavigation();
}

function resetInactivityTimer() {
    if (AppState.inactivityTimer) clearTimeout(AppState.inactivityTimer);

    // Auto-reset after 3 minutes of inactivity (except on welcome screen)
    if (AppState.currentScreen !== 'screen-welcome') {
        AppState.inactivityTimer = setTimeout(() => {
            startOver();
        }, 180000);
    }
}

// Reset timer on any interaction
document.addEventListener('touchstart', resetInactivityTimer);
document.addEventListener('click', resetInactivityTimer);
document.addEventListener('keydown', resetInactivityTimer);

// =============================================================================
// CSRF Token (Django)
// =============================================================================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Add CSRF token to all fetch requests
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    if (options.method && options.method !== 'GET') {
        const csrfToken = getCookie('csrftoken');
        if (csrfToken) {
            options.headers = options.headers || {};
            if (options.headers instanceof Headers) {
                options.headers.set('X-CSRFToken', csrfToken);
            } else {
                options.headers['X-CSRFToken'] = csrfToken;
            }
        }
    }
    return originalFetch(url, options);
};

// =============================================================================
// Initialization
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
    updateNavigation();
    console.log('MediKiosk initialized');
    // Initial welcome greeting in Hindi via Chatterbox / Sarvam AI TTS
    speakScreenContent('screen-welcome');
});

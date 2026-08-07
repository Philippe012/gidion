const API_BASE = '';
let currentSessionId = null;
let voiceEnabled = false;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

const messagesEl = document.getElementById('messages');
const textInput = document.getElementById('textInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const voiceToggle = document.getElementById('voiceToggle');
const newSessionBtn = document.getElementById('newSessionBtn');
const typingIndicator = document.getElementById('typingIndicator');
const chipsContainer = document.getElementById('chipsContainer');

async function init() {
    try {
        const response = await fetch(`${API_BASE}/api/session/new`, { method: 'POST' });
        const data = await response.json();
        currentSessionId = data.session_id;
        addMessage(data.message, 'assistant');
    } catch (e) {
        addMessage("Welcome! I'm Gidion, your clinical assistant. What symptoms can you tell me about?", 'assistant');
    }
}

async function sendMessage(text) {
    if (!text.trim()) return;

    addMessage(text, 'user');
    textInput.value = '';
    showTyping(true);
    hideChips();

    try {
        const response = await fetch(`${API_BASE}/api/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                text: text,
                voice_enabled: voiceEnabled
            })
        });

        const data = await response.json();
        showTyping(false);

        if (data.session_id) {
            currentSessionId = data.session_id;
        }

        const urgencyClass = data.urgency === 'critical' ? 'urgent' : '';
        const msgEl = addMessage(data.reply_text, 'assistant', urgencyClass);

        if (data.urgency && data.urgency !== 'normal' && data.urgency !== 'complete') {
            const badge = document.createElement('div');
            badge.className = `urgency-badge urgency-${data.urgency}`;
            badge.textContent = data.urgency.replace('_', ' ').toUpperCase();
            msgEl.insertBefore(badge, msgEl.firstChild);
        }

        if (data.audio_url) {
            playAudio(data.audio_url, msgEl);
        }

        if (voiceEnabled && data.auto_listen && !isRecording) {
            setTimeout(() => toggleRecording(), 800);
        }

        if (data.pending_confirmations && data.pending_confirmations.length > 0) {
            showChips(data.pending_confirmations);
        }

    } catch (error) {
        showTyping(false);
        addMessage("Sorry, I'm having trouble connecting. Please try again.", 'assistant');
    }
}

function addMessage(text, role, extraClass = '') {
    const div = document.createElement('div');
    div.className = `message ${role} ${extraClass}`;

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    div.innerHTML = `${escapeHtml(text)}<div class="message-time">${time}</div>`;

    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
}

function showTyping(show) {
    typingIndicator.style.display = show ? 'flex' : 'none';
    if (show) {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

function showChips(confirmations) {
    chipsContainer.innerHTML = '';
    confirmations.forEach(c => {
        const chip = document.createElement('button');
        chip.className = 'chip confirm';
        chip.innerHTML = `
            <i class="fas fa-check-circle"></i>
            ${c.field} = ${c.value}
        `;
        chip.onclick = () => {
            sendMessage(`Yes, ${c.field} is ${c.value}`);
            hideChips();
        };
        chipsContainer.appendChild(chip);

        const chipNo = document.createElement('button');
        chipNo.className = 'chip deny';
        chipNo.innerHTML = `
            <i class="fas fa-times-circle"></i>
            No
        `;
        chipNo.onclick = () => {
            sendMessage(`No, that's not correct`);
            hideChips();
        };
        chipsContainer.appendChild(chipNo);
    });
}

function hideChips() {
    chipsContainer.innerHTML = '';
}

function playAudio(url, parentEl) {
    const audio = new Audio(`${API_BASE}${url}`);

    const btn = document.createElement('button');
    btn.className = 'audio-btn';
    btn.innerHTML = '<i class="fas fa-play"></i> Play';

    btn.onclick = () => {
        audio.play().catch(e => console.log('Audio play failed:', e));
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Playing...';
    };

    if (parentEl) {
        parentEl.appendChild(btn);
    }

    if (voiceEnabled) {
        audio.play().catch(e => console.log('Auto-play failed:', e));
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Playing...';
    }

    audio.onended = () => {
        btn.innerHTML = '<i class="fas fa-redo"></i> Replay';
    };

    return audio;
}

// Voice recording
async function toggleRecording() {
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = e => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = async() => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const reader = new FileReader();
                reader.onloadend = async() => {
                    const base64 = reader.result.split(',')[1];
                    await sendAudio(base64);
                };
                reader.readAsDataURL(audioBlob);
                stream.getTracks().forEach(t => t.stop());
            };

            mediaRecorder.start();
            isRecording = true;
            micBtn.classList.add('recording');
            micBtn.innerHTML = '<i class="fas fa-stop"></i>';

        } catch (err) {
            addMessage('Microphone access denied or not available.', 'system');
        }
    } else {
        mediaRecorder.stop();
        isRecording = false;
        micBtn.classList.remove('recording');
        micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
    }
}

async function sendAudio(base64Audio) {
    showTyping(true);
    hideChips();

    try {
        const response = await fetch(`${API_BASE}/api/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                audio: base64Audio,
                voice_enabled: voiceEnabled
            })
        });

        const data = await response.json();
        showTyping(false);

        if (data.session_id) currentSessionId = data.session_id;

        const urgencyClass = data.urgency === 'critical' ? 'urgent' : '';
        const msgEl = addMessage(data.reply_text, 'assistant', urgencyClass);

        if (data.urgency && data.urgency !== 'normal' && data.urgency !== 'complete') {
            const badge = document.createElement('div');
            badge.className = `urgency-badge urgency-${data.urgency}`;
            badge.textContent = data.urgency.replace('_', ' ').toUpperCase();
            msgEl.insertBefore(badge, msgEl.firstChild);
        }

        if (data.audio_url) playAudio(data.audio_url, msgEl);
        if (data.pending_confirmations) showChips(data.pending_confirmations);

        // Auto-listen for voice loop
        if (voiceEnabled && data.auto_listen && !isRecording) {
            setTimeout(() => toggleRecording(), 800);
        }

    } catch (error) {
        showTyping(false);
        addMessage("Sorry, I couldn't process your voice message. Please try typing.", 'assistant');
    }
}

sendBtn.addEventListener('click', () => sendMessage(textInput.value));

textInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(textInput.value);
    }
});

micBtn.addEventListener('click', toggleRecording);

voiceToggle.addEventListener('click', () => {
    voiceEnabled = !voiceEnabled;

    voiceToggle.innerHTML = voiceEnabled ?
        '<i class="fas fa-volume-high"></i>' :
        '<i class="fas fa-volume-xmark"></i>';

    voiceToggle.classList.toggle('active', voiceEnabled);
    voiceToggle.title = voiceEnabled ? 'Voice On' : 'Voice Off';
});

newSessionBtn.addEventListener('click', async() => {
    currentSessionId = null;
    messagesEl.innerHTML = '';
    hideChips();
    await init();
});

init();
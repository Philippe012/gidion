import os
import sys
import base64
import tempfile
import re
from pathlib import Path
import flask.cli
flask.cli.show_server_banner = lambda *args, **kwargs: None
# from werkzeug.serving import run_simple
from waitress import serve

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS

from app import config
from app.core.conversation.manager import ConversationManager
from app.core.voice.stt import SpeechToText, VoiceUnavailableError as STTUnavailableError
from app.core.voice.tts import TextToSpeech, VoiceUnavailableError as TTSUnavailableError


app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Initialize conversation manager
conversation_manager = ConversationManager()

# Voice components (lazy init)
_stt = None
_tts = None

def get_stt():
    global _stt
    if _stt is None:
        _stt = SpeechToText()
    return _stt

def get_tts():
    global _tts
    if _tts is None:
        _tts = TextToSpeech()
    return _tts


@app.route("/")
def index():
    return render_template("index.html")


def _sanitize_filename(name: str) -> str:
    """Prevent path traversal in audio filenames."""
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '', name)


@app.route("/api/message", methods=["POST"])
def handle_message():
    """Single endpoint for all conversation."""
    session_id = None  # declare early so error handler can use it
    
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        text = data.get("text", "").strip()
        audio_base64 = data.get("audio")
        voice_enabled = data.get("voice_enabled", False)
        
        # Create session if needed
        if not session_id:
            session_id = conversation_manager.create_session()
        
        # Process audio if provided
        if audio_base64 and not text:
            try:
                audio_bytes = base64.b64decode(audio_base64)
                text = get_stt().transcribe_bytes(audio_bytes, source_suffix=".webm")
            except STTUnavailableError as e:
                return jsonify({
                    "session_id": session_id,
                    "reply_text": "Voice input isn't available right now. Please type your message.",
                    "urgency": "normal"
                })
            except Exception as e:
                print(f"STT error: {e}")
                return jsonify({
                    "session_id": session_id,
                    "reply_text": "I didn't catch that. Could you please repeat or type your message?",
                    "urgency": "normal"
                })
        
        if not text:
            return jsonify({
                "session_id": session_id,
                "reply_text": "I didn't receive any input. Please try again.",
                "urgency": "normal"
            })
        
        # Process message through conversation manager
        result = conversation_manager.handle_message(session_id, text)
        
        # Generate voice if requested
        audio_url = None
        if voice_enabled and result.reply_text:
            try:
                tts = get_tts()
                audio_bytes = tts.synthesize_to_bytes(result.reply_text)
                audio_dir = Path(tempfile.gettempdir()) / "gidion_audio"
                audio_dir.mkdir(exist_ok=True)
                safe_hash = os.urandom(4).hex()
                filename = f"response_{session_id[:8]}_{safe_hash}.wav"
                filename = _sanitize_filename(filename)
                audio_path = audio_dir / filename
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                audio_url = f"/api/audio/{filename}"
            except TTSUnavailableError:
                pass  # Silent fail, text still works
            except Exception as e:
                print(f"TTS error: {e}")
        
        return jsonify({
            "session_id": session_id,
            "reply_text": result.reply_text,
            "audio_url": audio_url,
            "pending_confirmations": result.pending_confirmations,
            "urgency": result.urgency,
            "assessment": result.assessment,
            "auto_listen": voice_enabled,
            "disclaimer": config.DISCLAIMER_TEXT
        })
    
    except Exception as e:
        print(f"Error in /api/message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "session_id": session_id or "unknown",
            "error": "Internal error",
            "reply_text": "I'm sorry, I encountered an error. Please try again."
        }), 500


@app.route("/api/audio/<filename>")
def serve_audio(filename):
    """Serve generated audio files."""
    filename = _sanitize_filename(filename)
    audio_dir = Path(tempfile.gettempdir()) / "gidion_audio"
    file_path = audio_dir / filename
    if file_path.exists() and file_path.is_file():
        return send_file(file_path, mimetype="audio/wav")
    return jsonify({"error": "Audio not found"}), 404


@app.route("/api/session/new", methods=["POST"])
def new_session():
    """Create new session."""
    session_id = conversation_manager.create_session()
    return jsonify({
        "session_id": session_id,
        "message": "Hello! I'm Gidion, your clinical assistant. What symptoms can you tell me about?"
    })


@app.route("/api/session/summary", methods=["GET"])
def session_summary():
    """Get conversation summary for a session."""
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "No session ID"}), 400
    
    from app.core.session.manager import SessionManager
    sm = SessionManager()
    state = sm.load_session(session_id)
    
    if not state:
        return jsonify({"error": "Session not found"}), 404
    
    facts_summary = "\n".join([f"{k}: {v}" for k, v in state.facts.items()]) or "No information recorded."
    
    return jsonify({
        "session_id": session_id,
        "facts": state.facts,
        "facts_summary": facts_summary,
        "assessment": state.assessment,
        "messages_count": len(state.conversation_history),
        "status": state.context.get("status", "active")
    })


def run():
    if sys.stdout is None or sys.stderr is None:
        devnull = open(os.devnull, 'w')
        sys.stdout = devnull
        sys.stderr = devnull
    
    serve(app, host=config.UI_HOST, port=config.UI_PORT, threads=4)


if __name__ == "__main__":
    run()
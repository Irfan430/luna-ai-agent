"""
LUNA AI Agent - Voice Engine v2.0
Author: IRFAN

Phase 2 Voice Mode Repair:
  - Passive wake word listening ("luna") in a separate async thread.
  - Immediate short acknowledgment: "Hmm?", "Yes?", "I'm listening."
  - Wake word detection does NOT block the main cognitive loop.
  - Silence timeout support.
  - Config options in config.yaml under 'voice:' key.
  - Graceful degradation if audio libraries not installed.

Required system dependencies:
  Linux:   sudo apt-get install portaudio19-dev python3-pyaudio
  macOS:   brew install portaudio && pip install pyaudio
  Windows: pip install pyaudio (pre-built wheel available)

Python packages:
  pip install pyttsx3 SpeechRecognition vosk sounddevice pyaudio
"""

import threading
import logging
import time
import queue
import random
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger("luna.voice.engine")

# ------------------------------------------------------------------
# Optional imports — graceful degradation
# ------------------------------------------------------------------

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("[VoiceEngine] pyttsx3 not installed. TTS disabled.")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("[VoiceEngine] SpeechRecognition not installed. STT disabled.")

try:
    import vosk
    import sounddevice as sd
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("[VoiceEngine] vosk/sounddevice not installed. Wake word detection disabled.")


# ------------------------------------------------------------------
# Acknowledgment phrases
# ------------------------------------------------------------------

ACKNOWLEDGMENTS = {
    "hmm":       ["Hmm?", "Mm?", "Hmm, yes?"],
    "yes":       ["Yes?", "Yes, go ahead.", "Yes, I'm here."],
    "listening": ["I'm listening.", "Listening.", "Go ahead."],
    "default":   ["Hmm?", "Yes?", "I'm listening."],
}


# ------------------------------------------------------------------
# Voice Engine
# ------------------------------------------------------------------

class VoiceEngine:
    """
    Personality-driven voice engine for LUNA.

    Supports:
    - Text-to-speech (TTS) via pyttsx3
    - Speech-to-text (STT) via SpeechRecognition / Google
    - Passive wake word detection via vosk (offline, async thread)
    - Silence timeout
    - Non-blocking main loop integration
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.voice_config = config.get("voice", {})
        self.enabled = self.voice_config.get("enabled", False)

        # Wake word config
        self.wake_word = self.voice_config.get("wake_word", "luna").lower()
        self.acknowledgment_enabled = self.voice_config.get("acknowledgment_enabled", True)
        self.acknowledgment_style = self.voice_config.get("acknowledgment_style", "default")
        self.passive_listening = self.voice_config.get("passive_listening", True)
        self.silence_timeout = self.voice_config.get("silence_timeout_seconds", 5)

        # Internal state
        self._wake_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._wake_callback: Optional[Callable] = None
        self._is_passive_active = False
        self._mic_active = False

        # TTS engine
        self._tts_engine = None
        self._tts_lock = threading.Lock()

        if self.enabled:
            self._init_tts()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _init_tts(self):
        """Initialize TTS engine safely."""
        if not TTS_AVAILABLE:
            logger.error("[VoiceEngine] pyttsx3 not available. TTS disabled.")
            return
        try:
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 150)
            self._tts_engine.setProperty("volume", 0.9)
            logger.info("[VoiceEngine] TTS engine initialized.")
        except Exception as e:
            logger.error(f"[VoiceEngine] TTS init failed: {e}")
            self._tts_engine = None

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    def speak(self, text: str):
        """Speak text using TTS. Thread-safe."""
        if not self.enabled or not self._tts_engine:
            return
        try:
            with self._tts_lock:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"[VoiceEngine] TTS error: {e}")

    def _get_acknowledgment(self) -> str:
        """Return a random acknowledgment phrase based on configured style."""
        phrases = ACKNOWLEDGMENTS.get(
            self.acknowledgment_style, ACKNOWLEDGMENTS["default"]
        )
        return random.choice(phrases)

    # ------------------------------------------------------------------
    # STT — active listening
    # ------------------------------------------------------------------

    def listen(self, timeout: int = None) -> Optional[str]:
        """
        Listen for voice input using SpeechRecognition.
        Returns transcribed text or None on failure/timeout.
        """
        if not self.enabled or not SR_AVAILABLE:
            return None

        timeout = timeout or self.silence_timeout

        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                self._mic_active = True
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("[VoiceEngine] Listening...")
                audio = recognizer.listen(source, timeout=timeout)
                self._mic_active = False
                text = recognizer.recognize_google(audio)
                return text
        except sr.WaitTimeoutError:
            logger.info("[VoiceEngine] Listening timeout.")
            self._mic_active = False
            return None
        except sr.UnknownValueError:
            logger.info("[VoiceEngine] Could not understand audio.")
            self._mic_active = False
            return None
        except Exception as e:
            logger.error(f"[VoiceEngine] STT error: {e}")
            self._mic_active = False
            return None

    # ------------------------------------------------------------------
    # Wake word detection — async thread (non-blocking)
    # ------------------------------------------------------------------

    def start_passive_listening(self, on_wake: Callable):
        """
        Start wake word detection in a separate daemon thread.
        Does NOT block the main cognitive loop.

        Args:
            on_wake: Callback invoked when wake word is detected.
        """
        if not self.passive_listening:
            logger.info("[VoiceEngine] Passive listening disabled in config.")
            return

        if not VOSK_AVAILABLE:
            logger.warning(
                "[VoiceEngine] vosk/sounddevice not installed. "
                "Wake word detection unavailable. "
                "Install with: pip install vosk sounddevice"
            )
            return

        if self._wake_thread and self._wake_thread.is_alive():
            logger.info("[VoiceEngine] Wake word thread already running.")
            return

        self._wake_callback = on_wake
        self._stop_event.clear()
        self._wake_thread = threading.Thread(
            target=self._wake_word_loop,
            daemon=True,
            name="luna-wake-word",
        )
        self._wake_thread.start()
        self._is_passive_active = True
        logger.info(f"[VoiceEngine] Passive wake word listening started. Wake word: '{self.wake_word}'")

    def stop_passive_listening(self):
        """Stop the wake word detection thread."""
        self._stop_event.set()
        self._is_passive_active = False
        if self._wake_thread:
            self._wake_thread.join(timeout=2.0)
        logger.info("[VoiceEngine] Passive listening stopped.")

    def _wake_word_loop(self):
        """
        Internal wake word detection loop running in a daemon thread.
        Uses vosk for offline, low-latency keyword spotting.
        Falls back to Google STT if vosk model not found.
        """
        try:
            import json as _json
            import vosk as _vosk

            model_path = self.voice_config.get("vosk_model_path", "vosk-model-small-en-us")
            try:
                model = _vosk.Model(model_path)
            except Exception:
                logger.warning(
                    f"[VoiceEngine] Vosk model not found at '{model_path}'. "
                    "Falling back to Google STT for wake word detection."
                )
                self._wake_word_loop_google()
                return

            recognizer = _vosk.KaldiRecognizer(model, 16000)
            audio_queue: queue.Queue = queue.Queue()

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"[VoiceEngine] Audio status: {status}")
                audio_queue.put(bytes(indata))

            import sounddevice as _sd
            with _sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=audio_callback,
            ):
                logger.info("[VoiceEngine] Vosk wake word stream active.")
                while not self._stop_event.is_set():
                    try:
                        data = audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if recognizer.AcceptWaveform(data):
                        result = _json.loads(recognizer.Result())
                        text = result.get("text", "").lower()
                        if self.wake_word in text:
                            self._handle_wake_detection(text)

        except Exception as e:
            logger.error(f"[VoiceEngine] Wake word loop error: {e}")
            self._is_passive_active = False

    def _wake_word_loop_google(self):
        """Fallback wake word loop using Google STT (requires internet)."""
        if not SR_AVAILABLE:
            return
        recognizer = sr.Recognizer()
        while not self._stop_event.is_set():
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=self.silence_timeout)
                text = recognizer.recognize_google(audio).lower()
                if self.wake_word in text:
                    self._handle_wake_detection(text)
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                logger.debug(f"[VoiceEngine] Google wake loop: {e}")
                time.sleep(0.5)

    def _handle_wake_detection(self, detected_text: str):
        """Handle wake word detection: acknowledge and invoke callback."""
        logger.info(f"[VoiceEngine] Wake word detected: '{detected_text}'")
        print(f"\n[VoiceEngine] Wake word detected!")

        if self.acknowledgment_enabled:
            ack = self._get_acknowledgment()
            print(f"LUNA: {ack}")
            self.speak(ack)

        if self._wake_callback:
            try:
                self._wake_callback(detected_text)
            except Exception as e:
                logger.error(f"[VoiceEngine] Wake callback error: {e}")

    # ------------------------------------------------------------------
    # Status indicators (for GUI)
    # ------------------------------------------------------------------

    @property
    def is_passive_active(self) -> bool:
        """Whether passive wake word listening is currently active."""
        return self._is_passive_active

    @property
    def is_mic_active(self) -> bool:
        """Whether the microphone is currently recording."""
        return self._mic_active

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def announce_execution(self, action: str):
        """Announce execution start."""
        if self.enabled:
            self.speak(f"Executing {action}")

    def announce_completion(self, success: bool):
        """Announce execution completion."""
        if self.enabled:
            if success:
                self.speak("Task completed successfully")
            else:
                self.speak("Task failed")

    def explain_error(self, error: str):
        """Explain error in voice."""
        if self.enabled:
            simplified = error.split(":")[0] if ":" in error else error
            self.speak(f"Error: {simplified}")

"""
LUNA AI Agent - Always-On Voice System v3.0
Author: IRFAN

Phase 4: Always-on Voice System
  - Continuous passive listening for wake word "Luna".
  - Immediate acknowledgment ("Hmm?", "Yes?", "I'm listening.").
  - Active listening for full command after wake word.
  - Background thread operation.
  - Graceful degradation if audio libraries not installed.
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

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    import vosk
    import sounddevice as sd
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

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
    """Continuous passive listening system for LUNA."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.voice_config = config.get("voice", {})
        self.enabled = self.voice_config.get("enabled", False)
        self.always_on = self.voice_config.get("always_on", True)
        self.wake_word = self.voice_config.get("wake_word", "luna").lower()
        self.acknowledgment_enabled = self.voice_config.get("acknowledgment_enabled", True)
        self.acknowledgment_style = self.voice_config.get("acknowledgment_style", "default")
        self.silence_timeout = self.voice_config.get("silence_timeout_seconds", 5)

        self._wake_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._wake_callback: Optional[Callable] = None
        self._is_passive_active = False
        self._mic_active = False

        self._tts_engine = None
        self._tts_lock = threading.Lock()

        if self.enabled:
            try:
                self._init_tts()
            except Exception as e:
                logger.error(f"Voice initialization failed: {e}")
                self.enabled = False

    def _init_tts(self):
        if not TTS_AVAILABLE: return
        try:
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 150)
            self._tts_engine.setProperty("volume", 0.9)
        except Exception as e:
            logger.error(f"TTS init failed: {e}")

    def speak(self, text: str):
        if not self.enabled or not self._tts_engine: return
        try:
            with self._tts_lock:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")

    def _get_acknowledgment(self) -> str:
        phrases = ACKNOWLEDGMENTS.get(self.acknowledgment_style, ACKNOWLEDGMENTS["default"])
        return random.choice(phrases)

    def listen(self, timeout: int = None) -> Optional[str]:
        if not self.enabled or not SR_AVAILABLE: return None
        timeout = timeout or self.silence_timeout
        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                self._mic_active = True
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=timeout)
                self._mic_active = False
                return recognizer.recognize_google(audio)
        except Exception:
            self._mic_active = False
            return None

    def start_passive_listening(self, on_wake: Callable):
        if not self.enabled or not self.always_on: return
        if self._wake_thread and self._wake_thread.is_alive(): return

        self._wake_callback = on_wake
        self._stop_event.clear()
        self._wake_thread = threading.Thread(target=self._wake_word_loop, daemon=True)
        self._wake_thread.start()
        self._is_passive_active = True
        logger.info(f"Passive listening started. Wake word: '{self.wake_word}'")

    def stop_passive_listening(self):
        self._stop_event.set()
        self._is_passive_active = False
        if self._wake_thread:
            self._wake_thread.join(timeout=2.0)

    def _wake_word_loop(self):
        # Simplified wake word loop using SpeechRecognition for broader compatibility
        if not SR_AVAILABLE: return
        recognizer = sr.Recognizer()
        while not self._stop_event.is_set():
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=2)
                text = recognizer.recognize_google(audio).lower()
                if self.wake_word in text:
                    self._handle_wake_detection(text)
            except Exception:
                continue

    def _handle_wake_detection(self, detected_text: str):
        if self.acknowledgment_enabled:
            ack = self._get_acknowledgment()
            print(f"LUNA: {ack}")
            self.speak(ack)

        if self._wake_callback:
            # Extract command if present after wake word
            command = detected_text.split(self.wake_word)[-1].strip()
            if command:
                self._wake_callback(command)
            else:
                # If no command, listen actively
                cmd = self.listen()
                if cmd: self._wake_callback(cmd)

    @property
    def is_passive_active(self) -> bool: return self._is_passive_active

    @property
    def is_mic_active(self) -> bool: return self._mic_active

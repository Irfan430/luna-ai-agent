"""
LUNA AI Agent - Always-On Voice System v4.0
Author: IRFAN

Phase 4: Always-on Voice Engine
  - Background voice thread.
  - Wake word: "Luna".
  - Soft response: "hmm?".
  - Non-blocking TTS.
  - Mic active even if GUI minimized.
"""

import threading
import logging
import time
import random
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger("luna.voice.engine")

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

class VoiceEngine:
    """Continuous passive listening system for LUNA."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.voice_config = config.get("voice", {})
        self.enabled = self.voice_config.get("enabled", False)
        self.wake_word = self.voice_config.get("wake_word", "luna").lower()
        
        self._stop_event = threading.Event()
        self._wake_thread: Optional[threading.Thread] = None
        self._wake_callback: Optional[Callable] = None
        self._tts_engine = None
        self._tts_lock = threading.Lock()

        if self.enabled:
            self._init_tts()

    def _init_tts(self):
        if not TTS_AVAILABLE: return
        try:
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 170)
            self._tts_engine.setProperty("volume", 0.8)
        except Exception as e:
            logger.error(f"TTS init failed: {e}")

    def speak(self, text: str):
        """Non-blocking TTS execution."""
        if not self.enabled or not self._tts_engine: return
        threading.Thread(target=self._speak_sync, args=(text,), daemon=True).start()

    def _speak_sync(self, text: str):
        try:
            with self._tts_lock:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")

    def start_passive_listening(self, on_wake: Callable):
        if not self.enabled or not SR_AVAILABLE: return
        self._wake_callback = on_wake
        self._stop_event.clear()
        self._wake_thread = threading.Thread(target=self._wake_word_loop, daemon=True)
        self._wake_thread.start()
        logger.info(f"Always-on voice engine started. Wake word: '{self.wake_word}'")

    def stop_passive_listening(self):
        self._stop_event.set()
        if self._wake_thread:
            self._wake_thread.join(timeout=1.0)

    def _wake_word_loop(self):
        recognizer = sr.Recognizer()
        while not self._stop_event.is_set():
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=2, phrase_time_limit=5)
                
                text = recognizer.recognize_google(audio).lower()
                if self.wake_word in text:
                    # Soft response
                    self.speak("hmm?")
                    
                    # Capture full command
                    command = text.split(self.wake_word)[-1].strip()
                    if not command:
                        # Listen for command if not in same phrase
                        with sr.Microphone() as source:
                            audio = recognizer.listen(source, timeout=3, phrase_time_limit=10)
                        command = recognizer.recognize_google(audio)
                    
                    if command and self._wake_callback:
                        self._wake_callback(command)
            except Exception:
                continue

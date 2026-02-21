"""
LUNA AI Agent - Always-On Voice System v5.0
Author: IRFAN

Structural Stabilization Refactor:
  - Background voice daemon thread.
  - Non-blocking STT and TTS.
  - Improved wake word detection and command capture.
  - Thread-safe voice operations.
"""

import threading
import logging
import time
import queue
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
    """Continuous passive listening system for LUNA (Daemon version)."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.voice_config = config.get("voice", {})
        self.enabled = self.voice_config.get("enabled", False)
        self.wake_word = self.voice_config.get("wake_word", "luna").lower()
        
        self._stop_event = threading.Event()
        self._wake_thread: Optional[threading.Thread] = None
        self._wake_callback: Optional[Callable] = None
        
        self._tts_queue = queue.Queue()
        self._tts_worker_thread: Optional[threading.Thread] = None
        self._tts_engine = None
        self._tts_lock = threading.Lock()

        if self.enabled:
            self._init_tts()

    def _init_tts(self):
        """Initialize TTS in a separate worker thread if possible."""
        if not TTS_AVAILABLE: return
        
        def tts_worker():
            try:
                # Engine must be initialized in the same thread it's used
                engine = pyttsx3.init()
                engine.setProperty("rate", 170)
                engine.setProperty("volume", 0.8)
                
                while not self._stop_event.is_set():
                    try:
                        text = self._tts_queue.get(timeout=1.0)
                        if text:
                            with self._tts_lock:
                                engine.say(text)
                                engine.runAndWait()
                        self._tts_queue.task_done()
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"TTS Error: {e}")
            except Exception as e:
                logger.error(f"TTS Worker init failed: {e}")

        self._tts_worker_thread = threading.Thread(target=tts_worker, daemon=True)
        self._tts_worker_thread.start()

    def speak(self, text: str):
        """Non-blocking TTS execution via queue."""
        if not self.enabled or not TTS_AVAILABLE: return
        self._tts_queue.put(text)

    def start_passive_listening(self, on_wake: Callable):
        """Start wake word detection in a background daemon thread."""
        if not self.enabled or not SR_AVAILABLE: return
        self._wake_callback = on_wake
        self._stop_event.clear()
        self._wake_thread = threading.Thread(target=self._wake_word_loop, daemon=True)
        self._wake_thread.start()
        logger.info(f"Always-on voice engine started. Wake word: '{self.wake_word}'")

    def stop_passive_listening(self):
        """Stop background listening."""
        self._stop_event.set()
        if self._wake_thread:
            self._wake_thread.join(timeout=1.0)

    def _wake_word_loop(self):
        """Background loop for wake word detection."""
        recognizer = sr.Recognizer()
        # Set higher sensitivity
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        
        while not self._stop_event.is_set():
            try:
                with sr.Microphone() as source:
                    # Quick ambient adjustment
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    # Listen for wake word
                    audio = recognizer.listen(source, timeout=2, phrase_time_limit=5)
                
                # Recognize via Google (requires internet)
                text = recognizer.recognize_google(audio).lower()
                
                if self.wake_word in text:
                    # Found wake word
                    logger.info("Wake word detected!")
                    self.speak("hmm?")
                    
                    # Try to capture the rest of the command from the same phrase
                    command = text.split(self.wake_word)[-1].strip()
                    
                    if not command:
                        # Listen specifically for the command
                        with sr.Microphone() as source:
                            audio = recognizer.listen(source, timeout=3, phrase_time_limit=10)
                        command = recognizer.recognize_google(audio)
                    
                    if command and self._wake_callback:
                        # Call the callback in a separate thread to avoid blocking mic
                        threading.Thread(target=self._wake_callback, args=(command,), daemon=True).start()
                        
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                logger.debug(f"Voice loop error: {e}")
                time.sleep(0.5)
                continue

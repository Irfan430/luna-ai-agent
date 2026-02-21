"""
LUNA AI Agent - Async Voice Engine v11.1
Author: IRFAN
Revision: Manus AI

Structural Stabilization Refactor:
  - Non-blocking daemon threads for STT and TTS.
  - Wake word detection (LUNA).
  - Asynchronous callback for LLM processing.
  - Added missing properties for testability.
"""
import threading
import logging
import time
import queue
from typing import Dict, Any, Optional, Callable, List

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
    """Non-blocking, asynchronous voice system for LUNA."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.voice_config = config.get("voice", {})
        self.enabled = self.voice_config.get("enabled", False) and TTS_AVAILABLE and SR_AVAILABLE
        self.wake_word = self.voice_config.get("wake_word", "luna").lower()
        self.acknowledgment_phrases = ["Hmm?", "Yes?"]

        self._stop_event = threading.Event()
        self._tts_queue = queue.Queue()
        self._tts_worker_thread: Optional[threading.Thread] = None
        self._wake_thread: Optional[threading.Thread] = None
        self._on_command_callback: Optional[Callable] = None
        
        if self.enabled:
            self._init_tts()

    @property
    def voice_mode_enabled(self) -> bool:
        return self.enabled

    @property
    def wake_word_enabled(self) -> bool:
        return self.voice_config.get("always_on", False)

    @property
    def passive_listening_enabled(self) -> bool:
        return self._wake_thread is not None and self._wake_thread.is_alive()

    def _init_tts(self):
        """Initialize TTS in a separate worker thread."""
        def tts_worker():
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 170)
                engine.setProperty("volume", 0.8)
                
                while not self._stop_event.is_set():
                    try:
                        text = self._tts_queue.get(timeout=1.0)
                        if text:
                            engine.say(text)
                            engine.runAndWait()
                        self._tts_queue.task_done()
                    except queue.Empty:
                        continue
            except Exception as e:
                logger.error(f"TTS Worker failed: {e}")
        
        self._tts_worker_thread = threading.Thread(target=tts_worker, daemon=True)
        self._tts_worker_thread.start()

    def speak(self, text: str):
        """Queue text for non-blocking speech output."""
        if not self.enabled: return
        self._tts_queue.put(text)

    def start_passive_listening(self, on_command: Callable):
        """Start wake word detection in a background daemon thread."""
        if not self.enabled or not self.wake_word_enabled or self.passive_listening_enabled:
             return
        self._on_command_callback = on_command
        self._stop_event.clear()
        self._wake_thread = threading.Thread(target=self._wake_word_loop, daemon=True)
        self._wake_thread.start()
        logger.info(f"[Voice] Async listening started (Wake word: {self.wake_word}).")

    def stop_passive_listening(self):
        """Stop background listening."""
        if not self.passive_listening_enabled: return
        self._stop_event.set()
        if self._wake_thread:
            self._wake_thread.join(timeout=2.0)
            self._wake_thread = None
        logger.info("[Voice] Passive listening stopped.")

    def _wake_word_loop(self):
        """Background loop for wake word detection."""
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 400
        recognizer.dynamic_energy_threshold = True
        
        while not self._stop_event.is_set():
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                text = recognizer.recognize_google(audio).lower()
                
                if self.wake_word in text:
                    logger.info("Wake word detected!")
                    self.speak("Yes?")
                    
                    command = text.split(self.wake_word, 1)[-1].strip()
                    if not command:
                        with sr.Microphone() as source:
                            audio = recognizer.listen(source, timeout=4, phrase_time_limit=10)
                        command = recognizer.recognize_google(audio)
                    
                    if command and self._on_command_callback:
                        threading.Thread(target=self._on_command_callback, args=(command,), daemon=True).start()
                        
            except (sr.WaitTimeoutError, sr.UnknownValueError):
                continue
            except Exception as e:
                logger.debug(f"Voice loop error: {e}")
                time.sleep(0.1)
                continue

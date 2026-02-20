"""
LUNA AI Agent - Voice Personality Engine
Author: IRFAN

Handles natural TTS and STT with task-aware awareness.
"""

import pyttsx3
import speech_recognition as sr
from typing import Dict, Any, Optional


class VoiceEngine:
    """Personality-driven voice engine for LUNA."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.voice_config = config.get('voice', {})
        self.enabled = self.voice_config.get('enabled', False)
        
        if self.enabled:
            # Initialize text-to-speech
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)  # Speed
            self.tts_engine.setProperty('volume', 0.9)  # Volume
            
            # Initialize speech recognition
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()

    def speak(self, text: str):
        """Speak text using TTS."""
        if not self.enabled:
            return
        
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")

    def listen(self, timeout: int = 5) -> Optional[str]:
        """Listen for voice input."""
        if not self.enabled:
            return None
        
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("Listening...")
                audio = self.recognizer.listen(source, timeout=timeout)
                text = self.recognizer.recognize_google(audio)
                return text
        except sr.WaitTimeoutError:
            print("Listening timeout")
            return None
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except Exception as e:
            print(f"Speech recognition error: {e}")
            return None

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
            simplified = error.split(':')[0] if ':' in error else error
            self.speak(f"Error: {simplified}")

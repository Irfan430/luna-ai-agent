"""
LUNA AI Agent - Voice Handler
Author: IRFAN

Voice input/output handler.
"""

from typing import Optional
import pyttsx3
import speech_recognition as sr
from config.config_loader import get_config


class VoiceHandler:
    """Handle voice input and output."""
    
    def __init__(self):
        """Initialize voice handler."""
        self.config = get_config()
        self.voice_config = self.config.get_voice_config()
        self.enabled = self.voice_config.get("enabled", False)
        
        if self.enabled:
            # Initialize text-to-speech
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)  # Speed
            self.tts_engine.setProperty('volume', 0.9)  # Volume
            
            # Initialize speech recognition
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
    
    def speak(self, text: str) -> None:
        """
        Speak text using TTS.
        
        Args:
            text: Text to speak
        """
        if not self.enabled:
            return
        
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")
    
    def listen(self, timeout: int = 5) -> Optional[str]:
        """
        Listen for voice input.
        
        Args:
            timeout: Listening timeout in seconds
            
        Returns:
            Recognized text or None
        """
        if not self.enabled:
            return None
        
        try:
            with self.microphone as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                print("Listening...")
                audio = self.recognizer.listen(source, timeout=timeout)
                
                # Recognize speech
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
    
    def announce_execution(self, action: str) -> None:
        """
        Announce execution start.
        
        Args:
            action: Action being executed
        """
        if self.enabled:
            self.speak(f"Executing {action}")
    
    def announce_completion(self, success: bool) -> None:
        """
        Announce execution completion.
        
        Args:
            success: Whether execution was successful
        """
        if self.enabled:
            if success:
                self.speak("Task completed successfully")
            else:
                self.speak("Task failed")
    
    def explain_error(self, error: str) -> None:
        """
        Explain error in voice.
        
        Args:
            error: Error message
        """
        if self.enabled:
            # Simplify error for voice
            simplified = error.split(':')[0] if ':' in error else error
            self.speak(f"Error: {simplified}")

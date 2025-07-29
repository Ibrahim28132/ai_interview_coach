import speech_recognition as sr
import pyttsx3
import pyaudio
import wave
import tempfile
import logging
import os
import asyncio
from typing import Optional
from config import Config
import openai


class VoiceInterface:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)
        self._last_response = None
        self._response_event = asyncio.Event()
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def speak(self, text: str):
        """Output text as speech if voice is enabled"""
        if not Config.VOICE_ENABLED:
            logging.debug(f"Text-to-speech: {text}")
            return

        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logging.error(f"Speech synthesis error: {e}")

    def set_response(self, response: str):
        """Set the response received from the UI"""
        self._last_response = response
        self._response_event.set()
        logging.debug(f"Response received from UI: {response}")

    async def wait_for_response(self, timeout: int = 60) -> Optional[str]:
        """Wait for a response with timeout, checking both UI and voice input"""
        self._response_event.clear()
        self._last_response = None

        try:
            # Wait for either UI response or voice input
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(self._response_event.wait()),
                    asyncio.create_task(self._listen_for_voice(timeout))
                ],
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel any pending tasks
            for task in pending:
                task.cancel()

            if self._last_response:
                return self._last_response
            return None

        except asyncio.TimeoutError:
            logging.debug("Response timeout reached")
            return None
        except Exception as e:
            logging.error(f"Error waiting for response: {e}")
            return None

    async def _listen_for_voice(self, timeout: int) -> Optional[str]:
        """Listen for voice input with timeout"""
        if not Config.VOICE_ENABLED:
            return None

        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=timeout)
                text = self.recognizer.recognize_google(audio)
                self._last_response = text
                self._response_event.set()
                return text
            except sr.WaitTimeoutError:
                logging.debug("Voice input timeout")
                return None
            except sr.UnknownValueError:
                logging.debug("Could not understand audio")
                return None
            except Exception as e:
                logging.error(f"Voice recognition error: {e}")
                return None

    def clear_response(self):
        """Clear the stored response"""
        self._last_response = None
        self._response_event.clear()
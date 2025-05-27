#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Speech-to-Text Transcription Module

Provides functionality to transcribe audio files to text using Whisper.
"""

import os
import threading
import whisper
import time
import ssl
import urllib.request
import tempfile
import sys

class Transcriber:
    """Class for transcribing audio to text using Whisper."""
    
    def __init__(self, model_name="tiny", local_model_path=None):
        """Initialize the transcriber with the specified model.
        
        Args:
            model_name: Name of the Whisper model to use
                (tiny, base, small, medium, large)
            local_model_path: Optional path to a local model file or directory
                If provided, this will be used instead of downloading the model
        """
        self.model_name = model_name
        self.local_model_path = local_model_path
        self.model = None
        self.is_loaded = False
        self.is_transcribing = False
        self._load_thread = None
        self._transcribe_thread = None
        self._callback = None
        self._result = None
        self._models_dir = os.path.join(tempfile.gettempdir(), "whisper_models")
        
        # Create models directory if it doesn't exist
        if not os.path.exists(self._models_dir):
            os.makedirs(self._models_dir, exist_ok=True)
    
    def load_model(self, callback=None):
        """Load the Whisper model in a background thread.
        
        Args:
            callback: Optional callback function to call when loading is complete
        """
        if self.is_loaded or (self._load_thread and self._load_thread.is_alive()):
            # Already loaded or loading
            return
        
        def _load():
            start_time = time.time()
            try:
                # On macOS, ensure certificate verification works or use workaround
                if sys.platform == 'darwin':
                    try:
                        # Try to install certificates for Python on macOS
                        import certifi
                        os.environ['SSL_CERT_FILE'] = certifi.where()
                    except ImportError:
                        # If certifi is not available, use a less secure workaround
                        # NOTE: This is only for development purposes, not recommended for production
                        ssl._create_default_https_context = ssl._create_unverified_context
                        print("Warning: Using unverified HTTPS context. This is not secure for production.")
                
                # Use local model path if provided
                if self.local_model_path and os.path.exists(self.local_model_path):
                    print(f"Loading model from local path: {self.local_model_path}")
                    self.model = whisper.load_model(self.local_model_path)
                else:
                    self.model = whisper.load_model(self.model_name)
                
                self.is_loaded = True
                load_time = time.time() - start_time
                print(f"Whisper model '{self.model_name}' loaded in {load_time:.2f} seconds")
                
                if callback:
                    callback(True)
            except Exception as e:
                print(f"Error loading Whisper model: {e}")
                print("""Please try one of the following solutions:
1. Install certifi: pip install certifi
2. For Mac users, run: /Applications/Python*/Install\ Certificates.command
3. Or download models manually to a local directory""")
                if callback:
                    callback(False)
        
        self._load_thread = threading.Thread(target=_load)
        self._load_thread.daemon = True
        self._load_thread.start()
    
    def transcribe(self, audio_file, callback=None):
        """Transcribe an audio file to text.
        
        Args:
            audio_file: Path to the audio file to transcribe
            callback: Function to call with the transcription result
        
        Returns:
            A boolean indicating if transcription started successfully
        """
        if not self.is_loaded:
            print("Model not loaded yet. Load the model first.")
            return False
        
        if self.is_transcribing:
            print("Already transcribing audio.")
            return False
        
        if not os.path.exists(audio_file):
            print(f"Audio file not found: {audio_file}")
            return False
        
        self.is_transcribing = True
        self._callback = callback
        
        def _transcribe():
            try:
                start_time = time.time()
                print(f"Starting transcription of {audio_file}")
                
                # Transcribe with Whisper
                result = self.model.transcribe(audio_file)
                self._result = result["text"].strip()
                
                transcribe_time = time.time() - start_time
                print(f"Transcription completed in {transcribe_time:.2f} seconds")
                
                if self._callback:
                    self._callback(self._result)
            except Exception as e:
                print(f"Error transcribing audio: {e}")
                if self._callback:
                    self._callback(None)
            finally:
                self.is_transcribing = False
        
        self._transcribe_thread = threading.Thread(target=_transcribe)
        self._transcribe_thread.daemon = True
        self._transcribe_thread.start()
        
        return True
    
    def get_last_result(self):
        """Get the result of the last transcription.
        
        Returns:
            The transcribed text or None
        """
        return self._result

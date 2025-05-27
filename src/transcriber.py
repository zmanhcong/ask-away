#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Transcriber Module

This module provides functionality for transcribing audio files using Whisper.
"""

import os
import sys
import time
import threading
import uuid
import torch
import whisper
import ssl
import urllib.request
import tempfile

class Transcriber:
    """Class for transcribing audio files using Whisper."""
    
    def __init__(self, model_name="large", device="cpu", local_model_path=None):
        """Initialize the transcriber.
        
        Args:
            model_name: Name of the Whisper model to use (default: "base")
            device: Device to use for inference (default: "cpu")
            local_model_path: Path to a local model file (default: None)
        """
        self.model_name = model_name
        self.device = device
        self.local_model_path = local_model_path
        self.model = None
        self.is_loaded = False
        self._load_thread = None
        self.is_transcribing = False
        self._callback = None
        self._transcribe_thread = None
        self._result = None
        # Track active transcription processes
        self.active_transcriptions = {}
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
                    self.model = whisper.load_model(self.model_name)  # Should be 'large' for best accuracy
                
                self.is_loaded = True
                load_time = time.time() - start_time
                print(f"[WHISPER] Model loaded: {self.model_name} in {load_time:.2f} seconds")
                
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
    
    def transcribe(self, audio_file, callback=None, is_chunk=False, chunk_id=None):
        """Transcribe an audio file.
        
        Args:
            audio_file: Path to the audio file
            callback: Function to call when transcription is complete
            is_chunk: Whether this is a chunk of a larger recording
            chunk_id: Identifier for the chunk when is_chunk is True
            
        Returns:
            The transcribed text or None if transcription started asynchronously
        """
        if not self.is_loaded:
            if callback:
                callback("Model not loaded yet. Please wait.", False, chunk_id if is_chunk else None)
            return None
        
        if not os.path.exists(audio_file):
            if callback:
                callback("Audio file not found.", False, chunk_id if is_chunk else None)
            return None
        
        # Generate a unique ID for this transcription if it's not a chunk or chunk_id is not provided
        if not is_chunk or chunk_id is None:
            transcription_id = str(uuid.uuid4())
        else:
            transcription_id = chunk_id
        
        # Start the transcription in a separate thread to avoid blocking UI
        thread = threading.Thread(
            target=self._transcribe_audio,
            args=(audio_file, callback, is_chunk, transcription_id)
        )
        thread.daemon = True
        thread.start()
        
        # Track this transcription thread
        self.active_transcriptions[transcription_id] = {
            'thread': thread,
            'audio_file': audio_file,
            'is_chunk': is_chunk
        }
        
        return transcription_id

    def _transcribe_audio(self, audio_file, callback, is_chunk=False, chunk_id=None):
        """Transcribe an audio file in a separate thread.
        
        Args:
            audio_file: Path to the audio file
            callback: Function to call when transcription is complete
            is_chunk: Whether this is a chunk of a larger recording
            chunk_id: Identifier for this transcription process
            
        Returns:
            The transcribed text or None if an error occurred
        """
        if not self.is_loaded:
            error_msg = "Model is not loaded. Please call load_model() first."
            print(error_msg)
            if callback:
                callback(error_msg, False, chunk_id if is_chunk else None)
            return None
            
        # Check if the file exists and has content
        if not os.path.exists(audio_file):
            error_msg = "Audio file does not exist"
            print(error_msg)
            if callback:
                callback(error_msg, False, chunk_id if is_chunk else None)
            return None
            
        file_size = os.path.getsize(audio_file)
        if file_size == 0:
            error_msg = "Audio file is empty"
            print(error_msg)
            if is_chunk and os.path.exists(audio_file) and "recording_chunk" in audio_file:
                try:
                    os.remove(audio_file)
                except Exception as e:
                    print(f"Error removing empty chunk file: {e}")
            if callback:
                callback("", True, chunk_id if is_chunk else None)  # Empty string indicates silent/empty chunk
            return ""
            
        try:
            # Check if the file is too small to contain meaningful audio
            if file_size < 1024:  # Less than 1KB is likely not a valid audio file
                raise ValueError("Audio file is too small to process")
                
            # Log before transcription
            print(f"[WHISPER] Transcribing: {audio_file}, size: {file_size} bytes, language: en, model: {self.model_name}")
            start_transcribe = time.time()
            result = self.model.transcribe(audio_file, language='en', fp16=False)  # Disable FP16 for CPU compatibility
            elapsed = time.time() - start_transcribe
            text = result["text"].strip()
            print(f"[WHISPER] Done: {audio_file}, took {elapsed:.2f} seconds. Result: {text[:50]}...")
            
            # If no text was transcribed, it might be silent or background noise
            if not text:
                text = ""  # Empty string indicates silent/empty chunk
            
            # Clean up temporary chunk files if this was a chunk
            if is_chunk and os.path.exists(audio_file) and "recording_chunk" in audio_file:
                try:
                    os.remove(audio_file)
                except Exception as e:
                    print(f"Error removing temporary chunk file: {e}")
            
            # Call the callback with the result
            if callback:
                callback(text, True, chunk_id if is_chunk else None)
            
            # Clean up completed transcription
            if chunk_id in self.active_transcriptions:
                del self.active_transcriptions[chunk_id]
            
            return text
            
        except Exception as e:
            error_msg = f"Error transcribing audio: {str(e)}"
            print(f"[WHISPER][ERROR] {error_msg}")
            
            # Clean up temporary chunk files on error
            if is_chunk and os.path.exists(audio_file) and "recording_chunk" in audio_file:
                try:
                    os.remove(audio_file)
                except Exception as e:
                    print(f"Error removing temporary chunk file after error: {e}")
            
            if callback:
                callback(error_msg, False, chunk_id if is_chunk else None)
            
            # Clean up failed transcription
            if chunk_id in self.active_transcriptions:
                del self.active_transcriptions[chunk_id]
            
            return None
    
    def get_last_result(self):
        """Get the result of the last transcription.
        
        Returns:
            The transcribed text or None
        """
        return self._result

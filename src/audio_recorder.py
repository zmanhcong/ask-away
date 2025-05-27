#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audio Recorder Module

Provides functionality to record audio from the microphone and save it to a file.
"""

import os
import tempfile
import sounddevice as sd
import numpy as np
import wave
import threading
import time
import queue

class AudioRecorder:
    """Class for recording audio from the microphone."""
    
    def __init__(self, sample_rate=16000, channels=1):
        """Initialize the audio recorder.
        
        Args:
            sample_rate: Sample rate for recording (default: 16000 Hz)
            channels: Number of audio channels (default: 1 - mono)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.frames = []
        self.temp_dir = tempfile.gettempdir()
        self.audio_filename = None
        self._data_queue = queue.Queue()
        self._recording_thread = None
    
    def start_recording(self, max_duration=10):
        """Start recording audio from the microphone.
        
        Args:
            max_duration: Maximum duration in seconds (default: 10)
            
        Returns:
            A boolean indicating if recording started successfully
        """
        if self.recording:
            return False
        
        self.frames = []
        self.recording = True
        
        # Start the recording in a separate thread
        self._recording_thread = threading.Thread(
            target=self._record_audio,
            args=(max_duration,)
        )
        self._recording_thread.daemon = True
        self._recording_thread.start()
        
        return True
    
    def stop_recording(self):
        """Stop the current recording.
        
        Returns:
            Path to the saved audio file or None if no recording
        """
        if not self.recording:
            return None
        
        self.recording = False
        
        # Wait for the recording thread to finish
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join()
        
        # Get all remaining data from the queue
        while not self._data_queue.empty():
            self.frames.append(self._data_queue.get())
        
        return self._save_audio()
    
    def _record_audio(self, max_duration):
        """Record audio from the microphone for the specified duration.
        
        Args:
            max_duration: Maximum duration in seconds
        """
        # Function to handle incoming audio data
        def callback(indata, frames, time, status):
            if status:
                print(f"Recording status: {status}")
            self._data_queue.put(indata.copy())
        
        # Start the recording stream
        try:
            with sd.InputStream(samplerate=self.sample_rate, 
                              channels=self.channels, 
                              callback=callback):
                start_time = time.time()
                while self.recording and (time.time() - start_time) < max_duration:
                    # Check every 100ms if we should stop
                    time.sleep(0.1)
                    
                # Stop recording
                self.recording = False
        except Exception as e:
            print(f"Error recording audio: {e}")
            self.recording = False
    
    def _save_audio(self):
        """Save the recorded audio frames to a WAV file.
        
        Returns:
            Path to the saved audio file or None if no frames
        """
        if not self.frames:
            return None
        
        # Convert the list of NumPy arrays to a single array
        data = np.concatenate(self.frames, axis=0)
        
        # Generate a unique filename based on timestamp
        filename = os.path.join(
            self.temp_dir, 
            f"recording_{int(time.time())}.wav"
        )
        
        # Save as WAV file
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.sample_rate)
                wf.writeframes((data * 32767).astype(np.int16).tobytes())
            
            self.audio_filename = filename
            return filename
        except Exception as e:
            print(f"Error saving audio: {e}")
            return None
    
    def get_last_recording_path(self):
        """Get the path to the last recorded audio file.
        
        Returns:
            Path to the last recorded audio file or None
        """
        return self.audio_filename

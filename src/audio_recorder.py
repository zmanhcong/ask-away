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
    
    def __init__(self, sample_rate=16000, channels=1, chunk_duration=2.0):
        """Initialize the audio recorder.
        
        Args:
            sample_rate: Sample rate for recording (default: 16000 Hz)
            channels: Number of audio channels (default: 1 - mono)
            chunk_duration: Duration of each audio chunk in seconds (default: 3.0)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.chunk_frames = int(self.sample_rate * self.chunk_duration)
        self.recording = False
        self.frames = []
        self.current_chunk = []
        self.temp_dir = tempfile.gettempdir()
        self.audio_filename = None
        self._data_queue = queue.Queue()
        self._recording_thread = None
        self._chunk_callback = None
    
    def start_recording(self, max_duration=30, chunk_callback=None):
        """Start recording audio from the microphone.
        
        Args:
            max_duration: Maximum duration in seconds (default: 30)
            chunk_callback: Function to call when a chunk is complete
                The callback receives the chunk file path
            
        Returns:
            A boolean indicating if recording started successfully
        """
        if self.recording:
            return False
        
        self.frames = []
        self.current_chunk = []
        self.recording = True
        self._chunk_callback = chunk_callback
        
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
        print("Available input devices:")
        print(sd.query_devices())
        def callback(indata, frames, time, status):
            if status:
                print(f"Recording status: {status}")
            # Just copy the float32 audio data
            self._data_queue.put(indata.copy())
        try:
            # Select the first available input device (or default)
            input_device = None
            devices = sd.query_devices()
            # Prefer MacBook Pro Microphone
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0 and 'MacBook Pro Microphone' in device['name']:
                    input_device = i
                    print(f"Using MacBook Pro Microphone (device {i}): {device['name']}")
                    break
            # If not found, fall back to first available
            if input_device is None:
                for i, device in enumerate(devices):
                    if device['max_input_channels'] > 0:
                        input_device = i
                        print(f"Using fallback input device {i}: {device['name']}")
                        break
            if input_device is None:
                print("Error: No input devices found!")
                self.recording = False
                return
            print(f"[AUDIO] Recording: sample_rate={self.sample_rate}, channels={self.channels}, device={input_device}")
            with sd.InputStream(device=input_device,
                                samplerate=self.sample_rate,
                                channels=self.channels,
                                dtype='float32',  # Always use float32
                                blocksize=int(self.sample_rate * 0.1),
                                callback=callback) as stream:
                print(f"Recording started with sample rate: {self.sample_rate} Hz")
                start_time = time.time()
                chunk_start_time = time.time()
                chunk_count = 0
                while self.recording and (time.time() - start_time) < max_duration:
                    if not self._data_queue.empty():
                        data = self._data_queue.get()
                        self.frames.append(data)
                        self.current_chunk.append(data)
                    current_time = time.time()
                    if current_time - chunk_start_time >= self.chunk_duration and self.current_chunk:
                        print(f"Processing chunk {chunk_count} with {len(self.current_chunk)} frames")
                        chunk_filename = self._save_audio_chunk(self.current_chunk, chunk_count)
                        chunk_count += 1
                        if self._chunk_callback and chunk_filename:
                            self._chunk_callback(chunk_filename)
                        self.current_chunk = []
                        chunk_start_time = current_time
                    time.sleep(0.01)
                if self.current_chunk and self.recording:
                    print(f"Processing final chunk {chunk_count} with {len(self.current_chunk)} frames")
                    chunk_filename = self._save_audio_chunk(self.current_chunk, chunk_count)
                    if self._chunk_callback and chunk_filename:
                        self._chunk_callback(chunk_filename)
                self.recording = False
                print("Recording stopped")
        except Exception as e:
            print(f"Error recording audio: {e}")
            import traceback
            traceback.print_exc()
            self.recording = False
    
    def _save_audio_chunk(self, chunk, chunk_index):
        """Save a single audio chunk to a file with detailed logging."""
        if not chunk:
            print(f"[AUDIO] Chunk {chunk_index}: No frames to save.")
            return None
        audio = np.concatenate(chunk)
        duration_sec = len(audio) / self.sample_rate
        print(f"[AUDIO] Chunk {chunk_index}: {len(chunk)} frames, {len(audio)} samples, duration {duration_sec:.2f}s, sample_rate {self.sample_rate}, channels {self.channels}")
        audio_int16 = (audio * 32767).astype(np.int16)
        filename = f"chunk_{chunk_index:03d}.wav"
        filepath = os.path.join(self.temp_dir, filename)
        with wave.open(filepath, 'wb') as wave_file:
            wave_file.setnchannels(self.channels)
            wave_file.setsampwidth(2)
            wave_file.setframerate(self.sample_rate)
            wave_file.writeframes(audio_int16.tobytes())
        file_size = os.path.getsize(filepath)
        print(f"[AUDIO] Chunk {chunk_index} saved: {filepath} ({file_size} bytes)")
        return filepath
        """Save a single audio chunk to a file.
        
        Args:
            chunk: List of float32 audio frames
            chunk_index: Index of the chunk
        
        Returns:
            Path to the saved chunk file or None on error
        """
        if not chunk:
            return None
        
        # Convert float32 to int16
        audio = np.concatenate(chunk)
        audio_int16 = (audio * 32767).astype(np.int16)
        
        # Save to WAV file
        filename = f"chunk_{chunk_index:03d}.wav"
        filepath = os.path.join(self.temp_dir, filename)
        with wave.open(filepath, 'wb') as wave_file:
            wave_file.setnchannels(self.channels)
            wave_file.setsampwidth(2)  # int16
            wave_file.setframerate(self.sample_rate)
            wave_file.writeframes(audio_int16.tobytes())
        
        return filepath
    
    def _save_audio(self):
        """Save the recorded audio to a file.
        
        Returns:
            Path to the saved audio file or None on error
        """
        if not self.frames:
            return None
        
        # Convert float32 to int16
        audio = np.concatenate(self.frames)
        audio_int16 = (audio * 32767).astype(np.int16)
        
        # Save to WAV file
        filename = "recording.wav"
        filepath = os.path.join(self.temp_dir, filename)
        with wave.open(filepath, 'wb') as wave_file:
            wave_file.setnchannels(self.channels)
            wave_file.setsampwidth(2)  # int16
            wave_file.setframerate(self.sample_rate)
            wave_file.writeframes(audio_int16.tobytes())
        
        self.audio_filename = filepath
        return filepath
    
    def get_last_recording_path(self):
        """Get the path to the last recorded audio file.
        
        Returns:
            Path to the last recorded audio file or None
        """
        return self.audio_filename

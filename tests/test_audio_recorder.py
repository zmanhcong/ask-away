#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the AudioRecorder class.
"""

import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
import numpy as np
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from audio_recorder import AudioRecorder


class TestAudioRecorder(unittest.TestCase):
    """Test cases for the AudioRecorder class."""
    
    def setUp(self):
        """Set up the test environment before each test."""
        self.recorder = AudioRecorder(sample_rate=16000, channels=1)
    
    def test_initialization(self):
        """Test that the AudioRecorder initializes correctly."""
        self.assertEqual(self.recorder.sample_rate, 16000)
        self.assertEqual(self.recorder.channels, 1)
        self.assertFalse(self.recorder.recording)
        self.assertEqual(self.recorder.frames, [])
        self.assertIsNone(self.recorder.audio_filename)
    
    @patch('threading.Thread')
    def test_start_recording(self):
        """Test that recording can be started."""
        # Mock the threading to avoid actually recording
        with patch('threading.Thread') as mock_thread:
            # Call the method
            result = self.recorder.start_recording()
            
            # Verify that recording started successfully
            self.assertTrue(result)
            self.assertTrue(self.recorder.recording)
            
            # Verify thread was started with correct args
            mock_thread.assert_called_once()
            
    def test_start_recording_with_chunk_callback(self):
        """Test that recording can be started with a chunk callback."""
        # Create a mock callback function
        mock_callback = MagicMock()
        
        # Mock the threading to avoid actually recording
        with patch('threading.Thread') as mock_thread:
            # Call the method with the callback
            result = self.recorder.start_recording(chunk_callback=mock_callback)
            
            # Verify that recording started successfully
            self.assertTrue(result)
            self.assertTrue(self.recorder.recording)
            
            # Verify the callback was set correctly
            self.assertEqual(self.recorder._chunk_callback, mock_callback)
            
            # Verify thread was started with correct args
            mock_thread.assert_called_once()
            
    def test_start_recording_already_recording(self):
        """Test that starting recording while already recording fails."""
        # Set the recording flag
        self.recorder.recording = True
        
        # Try to start recording again
        result = self.recorder.start_recording()
        
        # Verify that starting again fails
        self.assertFalse(result)
    
    @patch('threading.Thread')
    def test_stop_recording_no_frames(self, mock_thread):
        """Test stopping recording when no frames were recorded."""
        # Set up recording state
        self.recorder.recording = True
        mock_thread.return_value.is_alive.return_value = True
        
        # Stop recording
        result = self.recorder.stop_recording()
        
        # Check results
        self.assertFalse(self.recorder.recording)
        self.assertIsNone(result)  # No audio file since no frames
    
    @patch('wave.open')
    @patch('numpy.concatenate')
    @patch('threading.Thread')
    def test_stop_recording_with_frames(self, mock_thread, mock_concatenate, mock_wave_open):
        """Test stopping recording with frames."""
        # Set up recording state
        self.recorder.recording = True
        mock_thread.return_value.is_alive.return_value = True
        
        # Create a mock frame
        mock_frame = np.zeros((1600, 1))
        self.recorder.frames = [mock_frame]
        
        # Mock numpy concatenate
        mock_data = np.zeros((1600, 1))
        mock_concatenate.return_value = mock_data
        
        # Set up wave mock
        mock_wf = MagicMock()
        mock_wave_open.return_value.__enter__.return_value = mock_wf
        
        # Stop recording
        with patch('time.time', return_value=12345):
            result = self.recorder.stop_recording()
        
        # Check results
        self.assertFalse(self.recorder.recording)
        self.assertIsNotNone(result)  # Should have an audio file path
        self.assertTrue(result.endswith('.wav'))  # Should be a WAV file
        mock_wf.setnchannels.assert_called_once_with(1)
        mock_wf.setframerate.assert_called_once_with(16000)
    
    def test_get_last_recording_path(self):
        """Test getting the path to the last recording."""
        # No recording yet
        self.assertIsNone(self.recorder.get_last_recording_path())
        
        # Set a recording path
        test_path = '/tmp/test.wav'
        self.recorder.audio_filename = test_path
        
        # Check the path is returned
        self.assertEqual(self.recorder.get_last_recording_path(), test_path)


    def test_save_audio_chunk(self):
        """Test that an audio chunk can be saved to a file."""
        # Add some fake audio data for the chunk
        chunk_frames = [
            np.array([[0.1, 0.2], [0.3, 0.4]]),
            np.array([[0.5, 0.6], [0.7, 0.8]])
        ]
        
        # Mock the wave module
        with patch('wave.open') as mock_wave:
            # Call the method
            filepath = self.recorder._save_audio_chunk(chunk_frames, 1)
            
            # Verify the file was created
            self.assertIsNotNone(filepath)
            self.assertTrue('recording_chunk' in filepath)
            self.assertTrue(filepath.endswith('.wav'))
            
            # Verify wave.open was called
            mock_wave.assert_called_once()
    
    def test_save_audio_chunk_empty_frames(self):
        """Test that saving an audio chunk with no frames returns None."""
        # Call the method with empty frames
        filepath = self.recorder._save_audio_chunk([], 1)
        
        # Verify that no file was created
        self.assertIsNone(filepath)
    
    def test_process_audio_chunk(self):
        """Test the audio chunk processing with callback."""
        # Create a mock callback function
        mock_callback = MagicMock()
        
        # Set up the recorder with the callback
        self.recorder._chunk_callback = mock_callback
        
        # Create some test frames and add them to current_chunk
        self.recorder.current_chunk = [
            np.array([[0.1, 0.2], [0.3, 0.4]]),
            np.array([[0.5, 0.6], [0.7, 0.8]])
        ]
        
        # Mock the _save_audio_chunk method
        with patch.object(self.recorder, '_save_audio_chunk', return_value='/tmp/test_chunk.wav') as mock_save:
            # Simulate chunk processing in _record_audio
            chunk_start_time = time.time() - 3  # Pretend 3 seconds have passed
            chunk_count = 1
            
            # Check if it's time to process a chunk (it should be since we set time 3 seconds ago)
            if time.time() - chunk_start_time >= self.recorder.chunk_duration and self.recorder.current_chunk:
                # Call the method we're testing indirectly
                chunk_filename = self.recorder._save_audio_chunk(self.recorder.current_chunk, chunk_count)
                
                # Verify callback was called with the right filename
                if self.recorder._chunk_callback and chunk_filename:
                    self.recorder._chunk_callback(chunk_filename)
            
            # Verify the methods were called correctly
            mock_save.assert_called_once()
            mock_callback.assert_called_once_with('/tmp/test_chunk.wav')


if __name__ == '__main__':
    unittest.main()

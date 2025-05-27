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
    def test_start_recording(self, mock_thread):
        """Test starting audio recording."""
        # Mock the thread to avoid actual recording
        mock_thread.return_value.daemon = None
        
        # Start recording
        result = self.recorder.start_recording(max_duration=5)
        
        # Check results
        self.assertTrue(result)
        self.assertTrue(self.recorder.recording)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
    
    def test_start_recording_already_recording(self):
        """Test starting recording when already recording."""
        # Set recording state to True
        self.recorder.recording = True
        
        # Try to start recording
        result = self.recorder.start_recording()
        
        # Should return False and not change state
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


if __name__ == '__main__':
    unittest.main()

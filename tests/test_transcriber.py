#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Transcriber class.
"""

import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from transcriber import Transcriber


class TestTranscriber(unittest.TestCase):
    """Test cases for the Transcriber class."""
    
    def setUp(self):
        """Set up the test environment before each test."""
        with patch('whisper.load_model'):
            self.transcriber = Transcriber(model_name="large")
    
    def test_initialization(self):
        """Test that the Transcriber initializes correctly."""
        self.assertEqual(self.transcriber.model_name, "large")
        self.assertFalse(self.transcriber.is_loaded)
        self.assertFalse(self.transcriber.is_transcribing)
        self.assertIsNone(self.transcriber.model)
        self.assertIsNone(self.transcriber._result)
    
    @patch('threading.Thread')
    @patch('whisper.load_model')
    def test_load_model(self, mock_load_model, mock_thread):
        """Test loading the Whisper model."""
        # Mock the thread to avoid actually loading the model
        mock_thread.return_value.daemon = None
        
        # Define a test callback
        test_callback = MagicMock()
        
        # Load the model
        self.transcriber.load_model(callback=test_callback)
        
        # Check that the thread was started
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
    
    def test_load_model_already_loaded(self):
        """Test loading the model when it's already loaded."""
        # Mark the model as loaded
        self.transcriber.is_loaded = True
        
        # Create a mock for the thread
        with patch('threading.Thread') as mock_thread:
            # Try to load the model
            self.transcriber.load_model()
            
            # Thread should not be created
            mock_thread.assert_not_called()
    
    def test_transcribe_model_not_loaded(self):
        """Test transcribing audio when the model is not loaded."""
        # Model not loaded
        self.transcriber.is_loaded = False
        
        # Try to transcribe
        result = self.transcriber.transcribe("test.wav")
        
        # Should return False
        self.assertFalse(result)
    
    def test_transcribe_already_transcribing(self):
        """Test transcribing when already transcribing."""
        # Set up state
        self.transcriber.is_loaded = True
        self.transcriber.is_transcribing = True
        
        # Try to transcribe
        result = self.transcriber.transcribe("test.wav")
        
        # Should return False
        self.assertFalse(result)
    
    def test_transcribe_file_not_found(self):
        """Test transcribing a non-existent file."""
        # Set up state
        self.transcriber.is_loaded = True
        
        # Use a non-existent file
        non_existent_file = "/path/to/nonexistent/file.wav"
        
        # Try to transcribe
        result = self.transcriber.transcribe(non_existent_file)
        
        # Should return False
        self.assertFalse(result)
    
    @patch('os.path.exists', return_value=True)
    @patch('threading.Thread')
    def test_transcribe_success(self, mock_thread, mock_exists):
        """Test transcribing audio successfully."""
        # Set up state
        self.transcriber.is_loaded = True
        self.transcriber.model = MagicMock()
        mock_thread.return_value.daemon = None
        
        # Create test callback
        test_callback = MagicMock()
        
        # Try to transcribe
        result = self.transcriber.transcribe("test.wav", callback=test_callback)
        
        # Check results
        self.assertTrue(result)
        self.assertTrue(self.transcriber.is_transcribing)
        self.assertEqual(self.transcriber._callback, test_callback)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
    
    def test_transcribe(self):
        """Test transcribing an audio file."""
        # Mock the model and transcribe method
        mock_result = {"text": "test transcription"}
        self.transcriber.model = MagicMock()
        self.transcriber.model.transcribe.return_value = mock_result
        self.transcriber.is_loaded = True
        
        # Create a mock callback
        mock_callback = MagicMock()
        
        # Mock the os.path.exists function to return True
        with patch('os.path.exists', return_value=True):
            # Call the method
            transcription_id = self.transcriber.transcribe("test.wav", callback=mock_callback)
            
            # Verify a valid transcription ID was returned
            self.assertIsNotNone(transcription_id)
            
            # Verify the transcription was tracked
            self.assertIn(transcription_id, self.transcriber.active_transcriptions)
            
    def test_transcribe_chunk(self):
        """Test transcribing an audio chunk."""
        # Mock the model and transcribe method
        mock_result = {"text": "chunk transcription"}
        self.transcriber.model = MagicMock()
        self.transcriber.model.transcribe.return_value = mock_result
        self.transcriber.is_loaded = True
        
        # Create a mock callback
        mock_callback = MagicMock()
        
        # Set a specific chunk ID
        chunk_id = "test_chunk_123"
        
        # Mock the os.path.exists function to return True
        with patch('os.path.exists', return_value=True):
            # Call the method with chunk parameters
            result_id = self.transcriber.transcribe(
                "chunk.wav", 
                callback=mock_callback, 
                is_chunk=True, 
                chunk_id=chunk_id
            )
            
            # Verify the returned ID matches the chunk ID
            self.assertEqual(result_id, chunk_id)
            
            # Verify the transcription was tracked
            self.assertIn(chunk_id, self.transcriber.active_transcriptions)
    
    def test_get_last_result(self):
        """Test getting the last transcription result."""
        # No result yet
        self.assertIsNone(self.transcriber.get_last_result())
        
        # Set a test result
        test_result = "This is a test transcription."
        self.transcriber._result = test_result
        
        # Check the result is returned
        self.assertEqual(self.transcriber.get_last_result(), test_result)


if __name__ == '__main__':
    unittest.main()

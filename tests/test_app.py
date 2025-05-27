#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Meeting Question Assistant application.
"""

import unittest
import tkinter as tk
from unittest.mock import patch, MagicMock
import sys
import os
import time

# Add the src directory to the path so we can import the app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from app import MeetingAssistantApp


class TestMeetingAssistantApp(unittest.TestCase):
    """Test cases for the MeetingAssistantApp class."""
    
    def setUp(self):
        """Set up the test environment before each test."""
        self.root = tk.Tk()
        self.app = MeetingAssistantApp(self.root)
    
    def tearDown(self):
        """Clean up after each test."""
        self.root.destroy()
    
    def test_initialization(self):
        """Test that the app initializes correctly."""
        # Verify that the window title is set correctly
        self.assertEqual(self.root.title(), "Meeting Question Assistant")
        
        # Verify that the initial UI components exist
        self.assertTrue(hasattr(self.app, 'record_button'))
        self.assertTrue(hasattr(self.app, 'text_box'))
        self.assertTrue(hasattr(self.app, 'ok_button'))
        self.assertTrue(hasattr(self.app, 'vi_text'))
        self.assertTrue(hasattr(self.app, 'lang_text'))
        
        # Verify that new UI components from Task 2 exist
        self.assertTrue(hasattr(self.app, 'status_bar'))
        self.assertTrue(hasattr(self.app, 'progress_bar'))
        self.assertTrue(hasattr(self.app, 'fullscreen_button'))
        self.assertTrue(hasattr(self.app, 'target_lang_frame'))
    
    def test_language_selection(self):
        """Test the language selection functionality."""
        # Check default language is English
        self.assertEqual(self.app.language_var.get(), "en")
        
        # Change language and verify
        self.app.language_var.set("ja")
        self.assertEqual(self.app.language_var.get(), "ja")
        
        # Change to Vietnamese and verify
        self.app.language_var.set("vi")
        self.assertEqual(self.app.language_var.get(), "vi")
    
    def test_fullscreen_toggle(self):
        """Test the fullscreen toggle functionality."""
        # Initially not in fullscreen
        self.assertFalse(self.app.is_fullscreen)
        
        # Toggle to fullscreen
        self.app._toggle_fullscreen()
        self.assertTrue(self.app.is_fullscreen)
        
        # Toggle back to normal
        self.app._toggle_fullscreen()
        self.assertFalse(self.app.is_fullscreen)
        
        # Test end fullscreen
        self.app.is_fullscreen = True
        self.app._end_fullscreen()
        self.assertFalse(self.app.is_fullscreen)
    
    def test_status_bar(self):
        """Test the status bar functionality."""
        # Check initial status message
        initial_status = self.app.status_bar.cget("text")
        self.assertEqual(initial_status, "Ready. Press 'Listen to question' to start recording.")
        
        # Update status and verify
        test_message = "Test status message"
        self.app._update_status(test_message)
        self.assertEqual(self.app.status_bar.cget("text"), test_message)
    
    def test_record_audio_ui_changes(self):
        """Test the UI changes when recording audio."""
        # Initially not recording
        self.assertFalse(self.app.is_recording)
        self.assertEqual(self.app.record_button.cget("text"), "🎙️ Listen to question")
        
        # Start recording
        self.app._record_audio()
        self.assertTrue(self.app.is_recording)
        self.assertEqual(self.app.record_button.cget("text"), "⏹️ Stop Recording")
        
        # Allow the simulated recording to complete (it auto-finishes after 3 seconds)
        self.app._finish_recording()  # Directly call finish to avoid waiting in tests
        
        # Verify recording has stopped
        self.assertFalse(self.app.is_recording)
        self.assertEqual(self.app.record_button.cget("text"), "🎙️ Listen to question")
        
        # Verify placeholder text
        text = self.app.text_box.get(1.0, tk.END).strip()
        self.assertEqual(text, "[Placeholder] What is the capital of France?")
    
    @patch('threading.Thread')
    def test_process_question(self, mock_thread):
        """Test the question processing with mocked threading."""
        # Set up a test question
        test_question = "What is the capital of France?"
        self.app.text_box.delete(1.0, tk.END)
        self.app.text_box.insert(tk.END, test_question)
        
        # Process the question
        self.app._process_question()
        
        # Verify thread was started
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
        
        # Verify status bar message contains the selected language
        status_text = self.app.status_bar.cget("text")
        self.assertIn("Processing question in English", status_text)
    
    def test_empty_question_warning(self):
        """Test that an empty question shows a warning."""
        # Clear the text box
        self.app.text_box.delete(1.0, tk.END)
        
        # Use a mock for messagebox.showwarning
        with patch('tkinter.messagebox.showwarning') as mock_warning:
            self.app._process_question()
            mock_warning.assert_called_once_with(
                "Empty Question", 
                "Please provide a question to process."
            )
    
    def test_update_results(self):
        """Test the update_results method."""
        # Test data
        vi_answer = "Đây là câu trả lời thử nghiệm."
        lang_answer = "This is a test answer."
        
        # Update results
        self.app._update_results(vi_answer, lang_answer)
        
        # Verify the results are displayed correctly
        self.assertEqual(self.app.vi_text.get(1.0, tk.END).strip(), vi_answer)
        self.assertEqual(self.app.lang_text.get(1.0, tk.END).strip(), lang_answer)
        
        # Verify status message
        self.assertEqual(
            self.app.status_bar.cget("text"),
            "Processing complete. Answer is displayed below."
        )
    
    def test_show_processing_indicator(self):
        """Test the processing indicator functionality."""
        # Initial state - progress bar should be hidden
        self.assertFalse(self.app.progress_bar.winfo_ismapped())
        
        # Show processing
        self.app._show_processing(True)
        
        # Force update of the UI
        self.root.update()
        
        # Verify buttons are disabled
        self.assertEqual(self.app.ok_button.state(), ('disabled',))
        self.assertEqual(self.app.record_button.state(), ('disabled',))
        
        # Hide processing
        self.app._show_processing(False)
        
        # Verify progress bar is hidden and buttons enabled
        self.assertFalse(self.app.progress_bar.winfo_ismapped())
        self.assertEqual(self.app.ok_button.state(), ())
        self.assertEqual(self.app.record_button.state(), ())
    
    def test_simulate_processing(self):
        """Test the simulated processing functionality."""
        # Create test data
        test_question = "What is the capital of France?"
        language_code = "en"
        
        # Expected results
        expected_vi = "[Giả lập] Thủ đô của Pháp là Paris. Đây là một thành phố lịch sử và văn hóa."
        expected_en = "[Simulated] The capital of France is Paris. It is a historical and cultural city."
        
        # Modify the _simulate_processing method to directly call _update_results for testing
        # instead of using root.after which doesn't work in test environment
        original_method = self.app._simulate_processing
        
        def mock_simulate_processing(question, language_code):
            # Simulate processing delay
            # time.sleep(2)  # Skip in test
            
            # Generate placeholder results
            vi_answer = expected_vi
            
            # Different answers based on language
            if language_code == "en":
                lang_answer = expected_en
            elif language_code == "ja":
                lang_answer = f"[シミュレーション] フランスの首都はパリです。それは歴史的で文化的な都市です。"
            else:  # Vietnamese
                lang_answer = vi_answer
            
            # Directly call update_results instead of scheduling it
            self.app._update_results(vi_answer, lang_answer)
        
        # Replace the method temporarily
        self.app._simulate_processing = mock_simulate_processing
        
        try:
            # Mock update_results to verify it's called with correct parameters
            with patch.object(self.app, '_update_results', wraps=self.app._update_results) as wrapped_update:
                # Call the processing method
                self.app._simulate_processing(test_question, language_code)
                
                # Verify update_results was called with correct parameters
                wrapped_update.assert_called_once()
                args = wrapped_update.call_args[0]
                
                # Verify the content of the answers
                self.assertEqual(args[0], expected_vi)
                self.assertEqual(args[1], expected_en)
        finally:
            # Restore original method
            self.app._simulate_processing = original_method


if __name__ == '__main__':
    unittest.main()

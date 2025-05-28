#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Meeting Question Assistant Application

This application helps users record questions during meetings,
convert speech to text, and generate appropriate answers in multiple languages.
"""

import os
import tkinter as tk
from tkinter import ttk, font, messagebox
from dotenv import load_dotenv
from tkinter import scrolledtext
import threading
import time
import sys
import traceback

# Import custom modules
from audio_recorder import AudioRecorder
from transcriber import Transcriber
from fix_mac_certificates import fix_mac_certificates

# Load environment variables from .env file
load_dotenv()

class MeetingAssistantApp:
    """Main application class for the Meeting Question Assistant."""
    
    def __init__(self, root):
        """Initialize the application UI and components.
        
        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("Meeting Question Assistant")
        self.root.geometry("1000x800")  # Increased window size for better layout
        
        # Configure styles
        self._configure_styles()
        
        # Configure window for fullscreen capability
        self.is_fullscreen = False
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._end_fullscreen)
        
        # Recording state
        self.is_recording = False
        self.audio_file = None
        self.model_loaded = False
        
        # Set up the UI components
        self._setup_ui()
        
        # Status bar for showing app state - create this before starting any async operations
        self._create_status_bar()
        self._update_status("Initializing... Loading speech recognition model...")
        
        # Initialize audio recorder and transcriber
        # Try to fix SSL certificate issues on macOS
        cert_fixed = fix_mac_certificates()
        if not cert_fixed:
            messagebox.showwarning(
                "SSL Certificate Warning",
                """Python certificate verification may fail. The application will try to use
an unverified context for downloading models, which is less secure.

For proper security, consider one of these solutions:
1. Install certifi: pip install certifi
2. Run the macOS certificate installation script"""
            )
        
        self.audio_recorder = AudioRecorder(sample_rate=16000)
        import os
        whisper_model = os.getenv("WHISPER_MODEL", "medium")
        self.transcriber = Transcriber(model_name=whisper_model)
        
        # Now that status_bar exists, load the Whisper model in the background
        self.transcriber.load_model(callback=self._on_model_loaded)
    
    def _configure_styles(self):
        """Configure custom styles for the application."""
        # Get default font
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=11)
        
        # Configure styles
        style = ttk.Style()
        
        # Button styles
        style.configure("Record.TButton", font=(None, 12, "bold"), padding=10)
        style.configure("OK.TButton", font=(None, 12, "bold"), padding=8)
        
        # Frame styles
        style.configure("TFrame", background="#f5f5f5")
        style.configure("TLabelframe", background="#f5f5f5")
        style.configure("TLabelframe.Label", font=(None, 11, "bold"))
    
    def _toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode."""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        return "break"
    
    def _end_fullscreen(self, event=None):
        """Exit fullscreen mode."""
        self.is_fullscreen = False
        self.root.attributes("-fullscreen", False)
        return "break"
    
    def _setup_ui(self):
        """Set up the user interface components."""
        # Main frame with padding
        self.main_frame = ttk.Frame(self.root, padding="20")  # Increased padding
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top control frame
        top_frame = ttk.Frame(self.main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Application title
        title_label = ttk.Label(
            top_frame, 
            text="Meeting Question Assistant", 
            font=(None, 16, "bold")
        )
        title_label.pack(side=tk.LEFT, pady=5)
        
        # Fullscreen button
        self.fullscreen_button = ttk.Button(
            top_frame, 
            text="⛶ Fullscreen",
            command=self._toggle_fullscreen
        )
        self.fullscreen_button.pack(side=tk.RIGHT, padx=5)
        
        # Main content frame
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Record button with custom style - moved to top for better flow
        self.record_button = ttk.Button(
            content_frame, 
            text="🎙️ Listen to question",
            command=self._record_audio,
            style="Record.TButton"
        )
        self.record_button.pack(pady=15)  # Increased padding
        
        # Initially disable the record button until the model is loaded
        self.record_button.state(["disabled"])
        
        # Text box for displaying transcribed text
        self.text_frame = ttk.LabelFrame(content_frame, text="Question Text")
        self.text_frame.pack(fill=tk.BOTH, expand=True, pady=15)  # Increased padding

        # Use ScrolledText for better text display with scrollbar
        self.text_box = scrolledtext.ScrolledText(
            self.text_frame, 
            height=7,  # Increased height
            wrap=tk.WORD,
            font=(None, 13)  # Larger font
        )
        self.text_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)  # Increased padding
        
        # Controls frame (language selection and buttons)
        controls_frame = ttk.Frame(content_frame)
        controls_frame.pack(fill=tk.X, pady=15)  # Increased padding
        
        # Language selection
        lang_frame = ttk.LabelFrame(controls_frame, text="Output Language")
        lang_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Language options
        self.language_var = tk.StringVar(value="en")
        languages = [("English", "en"), ("Japanese", "ja"), ("Vietnamese", "vi")]
        
        # Create radio buttons for each language
        for i, (lang_name, lang_code) in enumerate(languages):
            rb = ttk.Radiobutton(
                lang_frame, 
                text=lang_name,
                value=lang_code,
                variable=self.language_var
            )
            rb.pack(side=tk.LEFT, padx=10, pady=5)
        
        # OK button with custom style
        ok_frame = ttk.Frame(controls_frame)
        ok_frame.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.ok_button = ttk.Button(
            ok_frame, 
            text="✅ OK",
            command=self._process_question,
            style="OK.TButton"
        )
        self.ok_button.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Results display in two columns
        self.results_frame = ttk.LabelFrame(content_frame, text="Answer")
        self.results_frame.pack(fill=tk.BOTH, expand=True, pady=15)  # Increased padding
        
        # Two-column display for results with improved layout
        results_columns = ttk.Frame(self.results_frame)
        results_columns.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)  # Increased padding
        
        # Configure equal column widths
        results_columns.columnconfigure(0, weight=1)  # First column gets equal weight
        results_columns.columnconfigure(1, weight=1)  # Second column gets equal weight
        
        # Vietnamese column - using grid instead of pack for better control
        vi_frame = ttk.LabelFrame(results_columns, text="Vietnamese")
        vi_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)  # Using grid
        
        self.vi_text = scrolledtext.ScrolledText(
            vi_frame, 
            wrap=tk.WORD,
            font=(None, 12)  # Increased font size
        )
        self.vi_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)  # Increased padding
        
        # Target language column - using grid for equal width
        self.target_lang_frame = ttk.LabelFrame(results_columns, text="Target Language")
        self.target_lang_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)  # Using grid
        
        self.lang_text = scrolledtext.ScrolledText(
            self.target_lang_frame, 
            wrap=tk.WORD,
            font=(None, 12)  # Increased font size
        )
        self.lang_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)  # Increased padding
        
        # Create a progress bar for showing processing status
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            content_frame,
            orient="horizontal",
            length=100,
            mode="indeterminate",
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        self.progress_bar.pack_forget()  # Hide initially
    
    def _create_status_bar(self):
        """Create a status bar at the bottom of the window."""
        self.status_bar = ttk.Label(
            self.root, 
            text="", 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _update_status(self, message):
        """Update the status bar message.
        
        Args:
            message: The message to display in the status bar
        """
        self.status_bar.config(text=message)
    
    def _show_processing(self, is_processing=True):
        """Show or hide the processing indicator.
        
        Args:
            is_processing: Whether processing is in progress
        """
        if is_processing:
            self.progress_bar.pack(fill=tk.X, pady=(5, 0))
            self.progress_bar.start(10)
            self.ok_button.state(["disabled"])
            self.record_button.state(["disabled"])
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.ok_button.state(["!disabled"])
            self.record_button.state(["!disabled"])
    
    def _on_model_loaded(self, success):
        """Callback for when the Whisper model is loaded.
        
        Args:
            success: Boolean indicating if the model loaded successfully
        """
        if success:
            self.model_loaded = True
            self._update_status("Ready. Press 'Listen to question' to start recording.")
            self.record_button.state(["!disabled"])
        else:
            self._update_status("Error loading speech recognition model. Check console for details.")
            messagebox.showerror(
                "Model Loading Error", 
                "Failed to load the speech recognition model. Please restart the application."
            )
    
    def _on_transcription_complete(self, text):
        """Callback for when transcription is complete.
        
        Args:
            text: The transcribed text or None if an error occurred
        """
        if text is not None:
            # Update the text box with the transcribed text
            self.text_box.delete(1.0, tk.END)
            self.text_box.insert(tk.END, text)
            self._update_status("Transcription complete. Edit the text if needed.")
        else:
            self._update_status("Error transcribing audio. Please try again.")
            messagebox.showerror(
                "Transcription Error", 
                "Failed to transcribe the audio. Please try recording again."
            )
        
        # Hide processing indicator
        self._show_processing(False)
        
        # Enable the record button
        self.record_button.state(["!disabled"])
    
    def _record_audio(self):
        """Record audio from the microphone and transcribe it."""
        # Check if the model is loaded
        if not self.model_loaded:
            messagebox.showinfo(
                "Model Loading", 
                "Please wait for the speech recognition model to finish loading."
            )
            return
        
        # Toggle recording state
        self.is_recording = not self.is_recording
        
        if self.is_recording:
            # Start recording
            self.record_button.configure(text="⏹️ Stop Recording")
            self._update_status("Recording... Speak now.")
            
            # Start actual recording
            success = self.audio_recorder.start_recording(max_duration=60)
            if not success:
                self.is_recording = False
                self.record_button.configure(text="🎙️ Listen to question")
                self._update_status("Error starting recording. Please try again.")
                messagebox.showerror(
                    "Recording Error", 
                    "Failed to start recording. Please check your microphone and try again."
                )
        else:
            # User manually stopped recording
            self._finish_recording()
    
    def _finish_recording(self):
        """Finish the recording process and start transcription."""
        # Stop recording state
        self.is_recording = False
        self.record_button.configure(text="🎙️ Listen to question")
        
        # Show processing indicator
        self._show_processing(True)
        
        # Temporarily disable the record button during processing
        self.record_button.state(["disabled"])
        
        # Stop the recording and get the audio file
        self.audio_file = self.audio_recorder.stop_recording()
        
        if self.audio_file:
            self._update_status("Recording finished. Transcribing audio...")
            
            # Start transcription
            success = self.transcriber.transcribe(
                self.audio_file,
                callback=self._on_transcription_complete
            )
            
            if not success:
                self._update_status("Error starting transcription. Please try again.")
                self._show_processing(False)
                self.record_button.state(["!disabled"])
                messagebox.showerror(
                    "Transcription Error", 
                    "Failed to start transcription. Please try recording again."
                )
        else:
            self._update_status("Error saving recording. Please try again.")
            self._show_processing(False)
            self.record_button.state(["!disabled"])
            messagebox.showerror(
                "Recording Error", 
                "Failed to save the recording. Please try again."
            )
    
    def _process_question(self):
        """Process the question text and generate an answer.
        
        This is a placeholder. Actual implementation will be added in Task 5.
        """
        question = self.text_box.get(1.0, tk.END).strip()
        language_code = self.language_var.get()
        
        # Show language name in the UI
        language_map = {"en": "English", "ja": "Japanese", "vi": "Vietnamese"}
        language_name = language_map.get(language_code, "Unknown")
        
        # Update the target language frame title
        self.target_lang_frame.configure(text=language_name)
        
        # Check if question is empty
        if not question:
            messagebox.showwarning(
                "Empty Question", 
                "Please provide a question to process."
            )
            return
        
        # Show processing indicator
        self._show_processing(True)
        self._update_status(f"Processing question in {language_name}...")
        
        # Simulate processing delay (this would be a real API call in the full implementation)
        threading.Thread(target=self._simulate_processing, args=(question, language_code)).start()
    
    def _simulate_processing(self, question, language_code):
        """Simulate the processing of the question (temporary placeholder).
        
        Args:
            question: The question text to process
            language_code: The target language code
        """
        # Simulate processing delay
        time.sleep(2)
        
        # Generate placeholder results
        vi_answer = f"[Giả lập] Thủ đô của Pháp là Paris. Đây là một thành phố lịch sử và văn hóa."
        
        # Different answers based on language
        if language_code == "en":
            lang_answer = f"[Simulated] The capital of France is Paris. It is a historical and cultural city."
        elif language_code == "ja":
            lang_answer = f"[シミュレーション] フランスの首都はパリです。それは歴史的で文化的な都市です。"
        else:  # Vietnamese
            lang_answer = vi_answer
        
        # Update UI in the main thread
        self.root.after(0, lambda: self._update_results(vi_answer, lang_answer))
    
    def _update_results(self, vi_answer, lang_answer):
        """Update the results display with the generated answers.
        
        Args:
            vi_answer: The answer in Vietnamese
            lang_answer: The answer in the target language
        """
        # Clear previous results
        self.vi_text.delete(1.0, tk.END)
        self.lang_text.delete(1.0, tk.END)
        
        # Display new results
        self.vi_text.insert(tk.END, vi_answer)
        self.lang_text.insert(tk.END, lang_answer)
        
        # Hide processing indicator
        self._show_processing(False)
        self._update_status("Processing complete. Answer is displayed below.")


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = MeetingAssistantApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

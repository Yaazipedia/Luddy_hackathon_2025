import os
import sys
import time
import threading
import queue
import logging
import argparse
import json
from datetime import datetime

import numpy as np
import pyaudio
import whisper
import wave

# Import the analysis modules
from extract_items import extract_action_items
from summarize_meeting import summarize_meeting
from email_summary import send_meeting_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('realtime_meeting.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Audio recording settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
SILENCE_THRESHOLD = 500  # Adjust based on your microphone sensitivity
SILENCE_DURATION = 1.0  # Seconds of silence to consider a pause

class RealtimeMeeting:
    def __init__(self, output_dir="realtime_meetings", model_name="base"):
        """
        Initialize the real-time meeting recorder and transcriber.
        
        Args:
            output_dir (str): Directory to save outputs
            model_name (str): Whisper model name to use
        """
        self.output_dir = output_dir
        self.model_name = model_name
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.transcript = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(output_dir, f"meeting_{self.session_id}")
        
        # Create output directories
        if not os.path.exists(self.session_dir):
            os.makedirs(self.session_dir, exist_ok=True)
        
        # Audio file path
        self.audio_path = os.path.join(self.session_dir, f"meeting_audio_{self.session_id}.wav")
        self.transcript_path = os.path.join(self.session_dir, f"meeting_transcript_{self.session_id}.txt")
        
        # Initialize Whisper model
        logger.info(f"Loading Whisper model: {model_name}...")
        self.model = whisper.load_model(model_name)
        logger.info("Model loaded successfully")
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        
    def start_recording(self):
        """Start recording from microphone."""
        if self.is_recording:
            logger.warning("Recording is already in progress")
            return
        
        self.is_recording = True
        self.audio_frames = []
        
        # Start the recording thread
        self.record_thread = threading.Thread(target=self._record_audio)
        self.record_thread.daemon = True
        self.record_thread.start()
        
        # Start the transcription thread
        self.transcribe_thread = threading.Thread(target=self._process_audio)
        self.transcribe_thread.daemon = True
        self.transcribe_thread.start()
        
        logger.info("Recording and transcription started")
        print("\n[Recording started. Speak clearly into your microphone.]")
        print("[Press Ctrl+C to stop recording and process the transcript.]\n")
        
    def _record_audio(self):
        """Record audio from microphone and add to queue."""
        stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        logger.info("Microphone stream opened")
        
        try:
            while self.is_recording:
                data = stream.read(CHUNK, exception_on_overflow=False)
                self.audio_frames.append(data)
                self.audio_queue.put(data)
                
                # Optional: Detect silence for segmentation
                audio_data = np.frombuffer(data, dtype=np.int16)
                if np.abs(audio_data).mean() < SILENCE_THRESHOLD:
                    time.sleep(0.1)  # Reduce CPU usage during silence
                
        except Exception as e:
            logger.error(f"Error in audio recording: {str(e)}")
        finally:
            stream.stop_stream()
            stream.close()
            logger.info("Microphone stream closed")
            
    def _process_audio(self):
        """Process audio segments and transcribe."""
        audio_buffer = []
        last_transcription_time = time.time()
        segment_duration = 5  # Process in 5-second segments
        samples_per_segment = int(RATE * segment_duration)
        
        try:
            while self.is_recording or not self.audio_queue.empty():
                # Get audio data from queue (non-blocking)
                try:
                    data = self.audio_queue.get(block=True, timeout=0.1)
                    audio_buffer.append(data)
                except queue.Empty:
                    continue
                
                buffer_samples = len(audio_buffer) * CHUNK
                current_time = time.time()
                
                # Process when we have enough audio or enough time has passed
                if (buffer_samples >= samples_per_segment or 
                    (current_time - last_transcription_time >= segment_duration and buffer_samples > 0)):
                    
                    # Convert buffer to numpy array
                    audio_data = np.frombuffer(b''.join(audio_buffer), dtype=np.int16).astype(np.float32) / 32768.0
                    
                    # Transcribe the segment
                    try:
                        result = self.model.transcribe(
                            audio_data, 
                            language="en",
                            fp16=False
                        )
                        
                        text = result["text"].strip()
                        if text:
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            self.transcript.append(f"[{timestamp}] {text}")
                            
                            # Print the transcription
                            print(f"\033[92m[{timestamp}]\033[0m {text}")
                            
                            # Save incremental transcript
                            with open(self.transcript_path, "a", encoding="utf-8") as f:
                                f.write(f"[{timestamp}] {text}\n")
                    
                    except Exception as e:
                        logger.error(f"Error in transcription: {str(e)}")
                    
                    # Reset buffer and timer
                    audio_buffer = []
                    last_transcription_time = current_time
                    
        except Exception as e:
            logger.error(f"Error in audio processing: {str(e)}")
            
    def stop_recording(self):
        """Stop the recording and finalize the transcript."""
        if not self.is_recording:
            logger.warning("No recording in progress")
            return
        
        logger.info("Stopping recording...")
        self.is_recording = False
        
        # Wait for threads to finish
        if hasattr(self, 'record_thread') and self.record_thread.is_alive():
            self.record_thread.join(timeout=2.0)
        
        if hasattr(self, 'transcribe_thread') and self.transcribe_thread.is_alive():
            self.transcribe_thread.join(timeout=5.0)
        
        # Save the audio file
        self._save_audio_file()
        
        # Generate the final transcript
        full_transcript = "\n".join(self.transcript)
        
        logger.info(f"Recording stopped. Audio saved to: {self.audio_path}")
        logger.info(f"Transcript saved to: {self.transcript_path}")
        
        print("\n[Recording stopped. Processing final transcript...]")
        return full_transcript
        
    def _save_audio_file(self):
        """Save recorded audio to a WAV file."""
        if not self.audio_frames:
            logger.warning("No audio frames to save")
            return
        
        try:
            with wave.open(self.audio_path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(self.audio_frames))
            
            logger.info(f"Audio saved to: {self.audio_path}")
        except Exception as e:
            logger.error(f"Error saving audio file: {str(e)}")
            
    def analyze_transcript(self, transcript_text):
        """Analyze the transcript to extract action items and summary."""
        print("\n[Analyzing meeting transcript...]")
        
        try:
            # Create subdirectories
            action_items_dir = os.path.join(self.session_dir, "action_items")
            summary_dir = os.path.join(self.session_dir, "summary")
            os.makedirs(action_items_dir, exist_ok=True)
            os.makedirs(summary_dir, exist_ok=True)
            
            # Extract action items
            action_items, action_items_path = extract_action_items(transcript_text, action_items_dir)
            
            # Generate summary
            summary, summary_path = summarize_meeting(transcript_text, summary_dir)
            
            # Create analysis report
            report = {
                "session_id": self.session_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "audio_file": self.audio_path,
                "transcript_file": self.transcript_path,
                "action_items_count": len(action_items),
                "action_items_file": action_items_path,
                "summary_file": summary_path,
                "key_topics": summary.get("key_topics", [])
            }
            
            # Save the report
            report_path = os.path.join(self.session_dir, f"meeting_report_{self.session_id}.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            
            print(f"\n[Analysis complete. Report saved to: {report_path}]")
            
            # Display some key information
            print("\n=== Meeting Analysis ===")
            print(f"Key Topics: {', '.join(summary.get('key_topics', ['None detected']))}")
            print(f"Action Items: {len(action_items)}")
            for i, item in enumerate(action_items, 1):
                print(f"  {i}. {item['action']} (Assigned to: {item['assigned_to']})")
            print(f"\nFull meeting report available at: {report_path}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error analyzing transcript: {str(e)}")
            print(f"\n[Error analyzing transcript: {str(e)}]")
            return None
        
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()
        logger.info("Resources cleaned up")

def main():
    """Main function to run the real-time meeting recorder."""
    parser = argparse.ArgumentParser(description='Real-time meeting recorder and transcriber')
    parser.add_argument('--output-dir', default='realtime_meetings', help='Directory to save outputs')
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small', 'medium', 'large'], 
                        help='Whisper model to use (smaller is faster, larger is more accurate)')
    parser.add_argument('--no-analysis', action='store_true', help='Skip analysis after recording')
    
    # Add email-related arguments
    parser.add_argument('--email', action='store_true', help='Send summary email after analysis')
    parser.add_argument('--recipients', nargs='+', help='Email addresses of meeting attendees')
    parser.add_argument('--smtp-server', help='SMTP server address')
    parser.add_argument('--smtp-port', type=int, default=587, help='SMTP server port')
    parser.add_argument('--sender-email', help='Sender email address')
    parser.add_argument('--sender-password', help='Sender email password')
    
    args = parser.parse_args()
    
    meeting = RealtimeMeeting(output_dir=args.output_dir, model_name=args.model)
    
    try:
        # Start recording
        meeting.start_recording()
        
        # Keep running until interrupted
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n[Stopping recording...]")
        transcript_text = meeting.stop_recording()
        
        # Analyze the transcript if requested
        report = None
        if not args.no_analysis and transcript_text:
            report = meeting.analyze_transcript(transcript_text)
            
            # Send email if requested
            if args.email and report and args.recipients and args.smtp_server and args.sender_email and args.sender_password:
                print("\n[Sending meeting summary email...]")
                report_path = os.path.join(meeting.session_dir, f"meeting_report_{meeting.session_id}.json")
                success = send_meeting_summary(
                    report_path,
                    args.recipients,
                    args.smtp_server,
                    args.smtp_port,
                    args.sender_email,
                    args.sender_password
                )
                if success:
                    print(f"[Email sent successfully to {len(args.recipients)} recipients]")
                else:
                    print("[Failed to send email. Check logs for details]")
            elif args.email and not (args.recipients and args.smtp_server and args.sender_email and args.sender_password):
                print("\n[Email requested but missing required parameters]")
                print("[Required: --recipients, --smtp-server, --sender-email, --sender-password]")
            
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        print(f"\n[Error: {str(e)}]")
        
    finally:
        meeting.cleanup()
        print("\n[Session ended. Thank you for using Real-time Meeting Transcriber!]")

if __name__ == "__main__":
    main()
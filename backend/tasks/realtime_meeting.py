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
from .extract_items import extract_action_items
from .summarize_meeting import summarize_meeting
from .email_summary import send_meeting_summary

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
SILENCE_THRESHOLD = 500
SILENCE_DURATION = 1.0

LANGUAGE_CODE_MAP = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
    "pt": "Portuguese", "ru": "Russian", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "ar": "Arabic", "hi": "Hindi", "bn": "Bengali", "tr": "Turkish", "nl": "Dutch",
    "sv": "Swedish", "fi": "Finnish", "pl": "Polish", "no": "Norwegian", "uk": "Ukrainian",
    "vi": "Vietnamese", "th": "Thai"
}

class RealtimeMeeting:
    def __init__(self, output_dir="realtime_meetings", model_name="base"):
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), output_dir)
        self.model_name = model_name
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.transcript = []
        self.language_code = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.output_dir, f"meeting_{self.session_id}")
        os.makedirs(self.session_dir, exist_ok=True)
        self.audio_path = os.path.join(self.session_dir, f"meeting_audio_{self.session_id}.wav")
        self.transcript_path = os.path.join(self.session_dir, f"meeting_transcript_{self.session_id}.txt")
        logger.info(f"Loading Whisper model: {model_name}...")
        self.model = whisper.load_model(model_name)
        logger.info("Model loaded successfully")
        self.audio = pyaudio.PyAudio()

    def start_recording(self):
        if self.is_recording:
            logger.warning("Recording is already in progress")
            return
        self.is_recording = True
        self.audio_frames = []
        self.record_thread = threading.Thread(target=self._record_audio, daemon=True)
        self.transcribe_thread = threading.Thread(target=self._process_audio, daemon=True)
        self.record_thread.start()
        self.transcribe_thread.start()
        logger.info("Recording and transcription started")
        print("\n[Recording started. Speak clearly into your microphone.]")
        print("[Press Ctrl+C to stop recording and process the transcript.]\n")

    def _record_audio(self):
        stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        logger.info("Microphone stream opened")
        try:
            while self.is_recording:
                data = stream.read(CHUNK, exception_on_overflow=False)
                self.audio_frames.append(data)
                self.audio_queue.put(data)
                audio_data = np.frombuffer(data, dtype=np.int16)
                if np.abs(audio_data).mean() < SILENCE_THRESHOLD:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in audio recording: {str(e)}")
        finally:
            stream.stop_stream()
            stream.close()
            logger.info("Microphone stream closed")

    def _process_audio(self):
        audio_buffer = []
        last_transcription_time = time.time()
        segment_duration = 5
        samples_per_segment = int(RATE * segment_duration)
        try:
            while self.is_recording or not self.audio_queue.empty():
                try:
                    data = self.audio_queue.get(timeout=0.1)
                    audio_buffer.append(data)
                except queue.Empty:
                    continue
                buffer_samples = len(audio_buffer) * CHUNK
                current_time = time.time()
                if buffer_samples >= samples_per_segment or (current_time - last_transcription_time >= segment_duration and buffer_samples > 0):
                    audio_data = np.frombuffer(b''.join(audio_buffer), dtype=np.int16).astype(np.float32) / 32768.0
                    try:
                        result = self.model.transcribe(audio_data, fp16=False)
                        text = result["text"].strip()
                        if text:
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            self.transcript.append(f"[{timestamp}] {text}")
                            print(f"\033[92m[{timestamp}]\033[0m {text}")
                            if not self.language_code and "language" in result:
                                self.language_code = result["language"]
                                full_language_name = LANGUAGE_CODE_MAP.get(self.language_code, self.language_code)
                                logger.info(f"Detected language: {full_language_name} ({self.language_code})")
                            with open(self.transcript_path, "a", encoding="utf-8") as f:
                                f.write(f"[{timestamp}] {text}\n")
                    except Exception as e:
                        logger.error(f"Error in transcription: {str(e)}")
                    audio_buffer = []
                    last_transcription_time = current_time
        except Exception as e:
            logger.error(f"Error in audio processing: {str(e)}")

    def stop_recording(self):
        if not self.is_recording:
            logger.warning("No recording in progress")
            return
        logger.info("Stopping recording...")
        self.is_recording = False
        if hasattr(self, 'record_thread') and self.record_thread.is_alive():
            self.record_thread.join(timeout=2.0)
        if hasattr(self, 'transcribe_thread') and self.transcribe_thread.is_alive():
            self.transcribe_thread.join(timeout=5.0)
        self._save_audio_file()
        full_transcript = "\n".join(self.transcript)
        logger.info(f"Recording stopped. Audio saved to: {self.audio_path}")
        logger.info(f"Transcript saved to: {self.transcript_path}")
        print("\n[Recording stopped. Processing final transcript...]")
        full_language_name = LANGUAGE_CODE_MAP.get(self.language_code, self.language_code or "Unknown")
        return full_transcript, full_language_name

    def _save_audio_file(self):
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

    def analyze_transcript(self, transcript_text, language="unknown"):
        print("\n[Analyzing meeting transcript...]")
        try:
            action_items_dir = os.path.join(self.session_dir, "action_items")
            summary_dir = os.path.join(self.session_dir, "summary")
            os.makedirs(action_items_dir, exist_ok=True)
            os.makedirs(summary_dir, exist_ok=True)
            action_items, action_items_path = extract_action_items(transcript_text, action_items_dir)
            summary, summary_path = summarize_meeting(transcript_text, summary_dir)
            report = {
                "session_id": self.session_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "language": language,
                "audio_file": self.audio_path,
                "transcript_file": self.transcript_path,
                "action_items_count": len(action_items),
                "action_items_file": action_items_path,
                "summary_file": summary_path,
                "key_topics": summary.get("key_topics", [])
            }
            report_path = os.path.join(self.session_dir, f"meeting_report_{self.session_id}.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            print(f"\n[Analysis complete. Report saved to: {report_path}]")
            print("\n=== Meeting Analysis ===")
            print(f"Language Detected: {language}")
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
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()
        logger.info("Resources cleaned up")

class RealtimeMeetingController:
    def __init__(self):
        self.meeting = None

    def start(self):
        if self.meeting and self.meeting.is_recording:
            return "Already recording"
        self.meeting = RealtimeMeeting()
        self.meeting.start_recording()
        return "Recording started"

    def stop(self):
        if self.meeting and self.meeting.is_recording:
            transcript, language = self.meeting.stop_recording()
            report = self.meeting.analyze_transcript(transcript, language)
            self.meeting.cleanup()
            return report
        return {"error": "No active recording"}
    
meeting_controller = RealtimeMeetingController()

def main():
    parser = argparse.ArgumentParser(description='Real-time meeting recorder and transcriber')
    parser.add_argument('--output-dir', default='realtime_meetings', help='Directory to save outputs')
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small', 'medium', 'large'], help='Whisper model to use')
    parser.add_argument('--no-analysis', action='store_true', help='Skip analysis after recording')
    parser.add_argument('--email', action='store_true', help='Send summary email after analysis')
    parser.add_argument('--recipients', nargs='+', help='Email addresses of meeting attendees')
    parser.add_argument('--smtp-server', help='SMTP server address')
    parser.add_argument('--smtp-port', type=int, default=587, help='SMTP server port')
    parser.add_argument('--sender-email', help='Sender email address')
    parser.add_argument('--sender-password', help='Sender email password')

    args = parser.parse_args()
    meeting = RealtimeMeeting(output_dir=args.output_dir, model_name=args.model)
    try:
        meeting.start_recording()
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[Stopping recording...]")
        transcript_text, language = meeting.stop_recording()
        report = None
        if not args.no_analysis and transcript_text:
            report = meeting.analyze_transcript(transcript_text, language=language)
            if args.email and report and args.recipients and args.smtp_server and args.sender_email and args.sender_password:
                print("\n[Sending meeting summary email...]")
                report_path = os.path.join(meeting.session_dir, f"meeting_report_{meeting.session_id}.json")
                success = send_meeting_summary(report_path, args.recipients, args.smtp_server, args.smtp_port, args.sender_email, args.sender_password)
                if success:
                    print(f"[Email sent successfully to {len(args.recipients)} recipients]")
                else:
                    print("[Failed to send email. Check logs for details]")
            elif args.email:
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
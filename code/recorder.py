import os
import pyaudio
import numpy as np
import wave
import threading
import logging
import time

from sentiment_analysis import analyze_conversation_sentiment, read_conversation_from_file  # Assuming your script is named sentiment_analysis.py
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Audio recording settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
SILENCE_THRESHOLD = 500
SILENCE_DURATION = 1.0

def list_audio_devices():
    """List all available audio input devices."""
    device_count = pyaudio.PyAudio().get_device_count()
    logger.info("Available audio devices:")
    for i in range(device_count):
        device_info = pyaudio.PyAudio().get_device_info_by_index(i)
        logger.info(f"Device {i}: {device_info['name']}")

class VirtualAudioRecorder:
    def __init__(self, output_dir="meeting_recordings"):
        self.output_dir = output_dir
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.audio_frames = []
        self.session_id = time.strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(output_dir, f"meeting_{self.session_id}")
        os.makedirs(self.session_dir, exist_ok=True)
        self.audio_path = os.path.join(self.session_dir, f"meeting_audio_{self.session_id}.wav")
    
    def start_recording(self, device_index=None):
        if self.is_recording:
            logger.warning("Recording is already in progress.")
            return

        self.is_recording = True
        self.audio_frames = []

        stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=device_index
        )

        def record_audio():
            try:
                while self.is_recording:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    self.audio_frames.append(data)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    if np.abs(audio_data).mean() < SILENCE_THRESHOLD:
                        time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error during recording: {e}")
            finally:
                stream.stop_stream()
                stream.close()
                logger.info("Recording stream closed.")

        threading.Thread(target=record_audio, daemon=True).start()
        logger.info("Recording started.")
    
    def stop_recording(self):
        if not self.is_recording:
            logger.warning("No recording is in progress.")
            return
        
        self.is_recording = False
        logger.info("Stopping recording...")
        self._save_audio_file()
        self._run_postprocessing_pipeline()

    def _save_audio_file(self):
        if not self.audio_frames:
            logger.warning("No audio recorded.")
            return

        try:
            with wave.open(self.audio_path, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b"".join(self.audio_frames))
            logger.info(f"Audio saved to: {self.audio_path}")
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")

    def _run_postprocessing_pipeline(self):
        try:
            from process_audio import process_meeting

            logger.info("Running post-recording analysis...")
            results = process_meeting(self.audio_path)

            logger.info(f"Meeting analysis complete. Report: {results['report_path']}")

            # ===== SENTIMENT ANALYSIS HOOK =====
            transcript_path = results["transcript_path"]
            sentiment_output_path = os.path.join(
                os.path.dirname(transcript_path).replace("transcript", "sentiment"),
                "sentiment_results.json"
            )

            # Ensure output directory exists
            os.makedirs(os.path.dirname(sentiment_output_path), exist_ok=True)

            # Read the transcript
            conversation_text = read_conversation_from_file(transcript_path)
            if conversation_text:
                sentiment_results = analyze_conversation_sentiment(conversation_text)
                with open(sentiment_output_path, "w", encoding="utf-8") as f:
                    json.dump(sentiment_results, f, indent=2, ensure_ascii=False)
                logger.info(f"Sentiment results saved to: {sentiment_output_path}")
            else:
                logger.warning("Transcript not found or empty, skipping sentiment analysis.")

        except Exception as e:
            logger.error(f"Post-analysis failed: {e}")


    def get_device_index(self):
        device_count = self.audio.get_device_count()
        for i in range(device_count):
            device_info = self.audio.get_device_info_by_index(i)
            if "Virtual" in device_info["name"]:  # adjust for your device
                return i
        return None

if __name__ == "__main__":
    list_audio_devices()
    recorder = VirtualAudioRecorder()
    
    device_index = recorder.get_device_index() or 4  # Default fallback
    recorder.start_recording(device_index=device_index)

    logger.info("Recording for 30 seconds...")
    time.sleep(30)

    recorder.stop_recording()

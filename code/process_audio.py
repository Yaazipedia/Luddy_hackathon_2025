import os
import whisper
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_audio(audio_file_path, output_dir="transcripts"):
    """
    Process an audio file and convert it to text using Whisper.
    
    Args:
        audio_file_path (str): Path to the audio file
        output_dir (str): Directory to save the transcript
        
    Returns:
        str: Path to the saved transcript file
        str: The transcript text
    """
    logger.info(f"Processing audio file: {audio_file_path}")
    
    if not os.path.exists(audio_file_path):
        error_msg = f"Audio file not found: {audio_file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")
        
        # Load Whisper model
        logger.info("Loading Whisper model...")
        model = whisper.load_model("base")
        
        # Transcribe the audio
        logger.info("Transcribing audio...")
        result = model.transcribe(audio_file_path)
        transcript_text = result["text"]
        
        # Generate output filename based on input filename and timestamp
        base_filename = os.path.splitext(os.path.basename(audio_file_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{base_filename}_transcript_{timestamp}.txt"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save transcript to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        
        logger.info(f"Transcript saved to: {output_path}")
        return output_path, transcript_text
        
    except Exception as e:
        logger.error(f"Error processing audio file: {str(e)}")
        raise
        
if __name__ == "__main__":
    # Example usage
    try:
        transcript_path, text = process_audio("sample_meeting.mp3")
        print(f"Transcript saved to: {transcript_path}")
        print(f"First 100 characters: {text[:100]}...")
    except Exception as e:
        print(f"Error: {str(e)}")
import os
import whisper
import logging
from datetime import datetime
import numpy as np
import torch
import librosa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_audio(audio_file_path, output_dir="transcripts"):
    """
    Process an audio file and convert it to text using Whisper with basic speaker segmentation.
    
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
        
        # Transcribe the audio with word-level timestamps
        logger.info("Transcribing audio with word timestamps...")
        result = model.transcribe(audio_file_path, word_timestamps=True)
        
        # Get basic segmentation using speaker changes
        logger.info("Performing basic speaker segmentation...")
        segments_with_speakers = segment_speakers(audio_file_path, result["segments"])
        
        # Format transcript with speaker information
        transcript_text = format_transcript(segments_with_speakers)
        
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

def segment_speakers(audio_file_path, segments):
    """
    Perform basic speaker segmentation using audio features.
    
    Args:
        audio_file_path (str): Path to the audio file
        segments (list): Segments from Whisper transcription
        
    Returns:
        list: Segments with added speaker information
    """
    try:
        # Load audio file
        y, sr = librosa.load(audio_file_path, sr=None)
        
        # Extract MFCC features for speaker differentiation
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # For each segment, extract features and prepare for clustering
        segment_features = []
        for segment in segments:
            start_frame = int(segment["start"] * sr)
            end_frame = min(int(segment["end"] * sr), len(y))
            
            if start_frame < end_frame:
                segment_audio = y[start_frame:end_frame]
                if len(segment_audio) > 0:
                    # Extract MFCCs for this segment
                    seg_mfccs = librosa.feature.mfcc(y=segment_audio, sr=sr, n_mfcc=13)
                    mfcc_mean = np.mean(seg_mfccs, axis=1)
                    segment_features.append(mfcc_mean)
                else:
                    segment_features.append(np.zeros(13))
            else:
                segment_features.append(np.zeros(13))
        
        # Use a simple clustering approach with maximum of 2 speakers
        if len(segment_features) > 1:
            segment_features = np.array(segment_features)
            
            # Simple approach: Use K-means clustering with 2 potential speakers
            from sklearn.cluster import KMeans
            num_speakers = min(2, len(segment_features))
            kmeans = KMeans(n_clusters=num_speakers, random_state=0, n_init=10).fit(segment_features)
            speaker_labels = kmeans.labels_
        else:
            speaker_labels = [0] * len(segments)
        
        # Add speaker information to segments
        segments_with_speakers = []
        for i, segment in enumerate(segments):
            speaker_label = f"Speaker_{speaker_labels[i]+1}" if i < len(speaker_labels) else "Unknown"
            segment_with_speaker = segment.copy()
            segment_with_speaker["speaker"] = speaker_label
            segments_with_speakers.append(segment_with_speaker)
            
        return segments_with_speakers
        
    except Exception as e:
        logger.error(f"Error in speaker segmentation: {str(e)}")
        # Return original segments without speaker information
        return [{"speaker": "Speaker", **segment} for segment in segments]

def format_transcript(segments_with_speakers):
    """
    Format transcript with speaker information.
    
    Args:
        segments_with_speakers (list): Segments with speaker information
        
    Returns:
        str: Formatted transcript
    """
    transcript_text = ""
    current_speaker = None
    
    for segment in segments_with_speakers:
        speaker = segment.get("speaker", "Unknown")
        
        # Add speaker label if it's different from the previous one
        if speaker != current_speaker:
            transcript_text += f"\n\n[{speaker}]:\n"
            current_speaker = speaker
        
        # Add the text
        transcript_text += segment.get("text", "") + " "
    
    return transcript_text.strip()

if __name__ == "__main__":
    # Example usage
    try:
        transcript_path, text = process_audio("sample_meeting.mp3")
        print(f"Transcript saved to: {transcript_path}")
        print(f"First 100 characters: {text[:100]}...")
    except Exception as e:
        print(f"Error: {str(e)}")
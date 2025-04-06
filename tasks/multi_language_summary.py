import argparse
import json
import os
import subprocess
import tempfile
import requests
from googletrans import Translator

language_options = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "chinese": "zh-CN",
    "japanese": "ja",
    "hindi": "hi",
}

def convert_audio_to_wav(input_file):
    """Convert audio file to WAV format compatible with speech recognition."""
    try:
        # Check if ffmpeg exists
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: ffmpeg not found. Please install ffmpeg to enable audio conversion.")
        return None

    print(f"Converting {input_file} to WAV format...")
    temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    
    try:
        subprocess.run([
            "ffmpeg", "-i", input_file, 
            "-ar", "16000",  # 16kHz sample rate
            "-ac", "1",      # Mono
            "-c:a", "pcm_s16le",  # 16-bit PCM
            "-y",            # Overwrite output
            temp_wav
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        print(f"Audio converted successfully")
        return temp_wav
    except subprocess.SubprocessError as e:
        print(f"Error converting audio: {e}")
        if os.path.exists(temp_wav):
            os.unlink(temp_wav)
        return None

def transcribe_audio_with_whisper(audio_file_path, language_code):
    """Transcribe audio using OpenAI's Whisper model via API."""
    # This is a placeholder for actual implementation
    # In a real implementation, you would use a Whisper API or local model
    print(f"Transcribing audio in {language_code}...")
    
    # For the purpose of this example, we'll use a simple command-line approach
    # with whisper (if installed)
    try:
        result = subprocess.run(
            ["whisper", audio_file_path, "--language", language_code, "--model", "base"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        transcription = result.stdout
        return transcription
    except (subprocess.SubprocessError, FileNotFoundError):
        # If whisper isn't installed, fallback to a simpler approach
        print("Whisper not available. Using fallback transcription method...")
        
        # Simplified fallback for demonstration
        # In a real scenario, you might use a different API or library
        return f"[Transcription would happen here for {language_code}]"

def translate_text_simple(text, source_lang_code, target_lang_code):
    """Translate text using a simpler and faster method."""
    if source_lang_code == target_lang_code:
        return text
    
    try:
        print(f"Translating from {source_lang_code} to {target_lang_code}...")
        translator = Translator()
        result = translator.translate(text, src=source_lang_code, dest=target_lang_code)
        return result.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def summarize_text_simple(text, max_sentences=5):
    """Generate a simple extractive summary by selecting important sentences."""
    if not text or len(text.split()) < 50:
        return "Text too short for summarization"
    
    # Very simple summarization - just get first few sentences
    # In a real implementation, you'd use a more sophisticated algorithm
    sentences = text.split('. ')
    summary = '. '.join(sentences[:max_sentences]) + '.'
    return summary

def save_results(original_text, translated_text, summary, output_file):
    """Save results to JSON file."""
    results = {
        "original_transcription": original_text,
        "translated_text": translated_text,
        "summary": summary
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"Results saved to {output_file}")
    return results

def multi_language_summary(audio_file: str, source_lanugage: str, target_language: str):
    wav_file = convert_audio_to_wav(audio_file)
    if not wav_file:
        print("Failed to convert audio file. Please check the format.")
        return
    
    # Transcribe
    original_text = transcribe_audio_with_whisper(wav_file, language_options[source_lanugage.lower()])
    print("\nOriginal Transcription:")
    print(original_text)
    
    # Clean up temp file
    if os.path.exists(wav_file):
        os.unlink(wav_file)
    
    # Translate
    if language_options[source_lanugage.lower()] != language_options[target_language.lower()]:
        translated_text = translate_text_simple(original_text, language_options[source_lanugage.lower()], language_options[target_language.lower()])
        print(f"\nTranslated to {target_language.lower()}:")
        print(translated_text)
    else:
        translated_text = original_text
        print("\nNo translation needed (same source and target language)")
    
    # Summarize
    summary = summarize_text_simple(translated_text)
    print(f"\nSummary in {target_language.lower()}:")
    print(summary)
    
    # Save results
    save_results(original_text, translated_text, summary, "translation_result.json")

def main():
    parser = argparse.ArgumentParser(description='Fast multilingual audio transcription and translation')
    parser.add_argument('audio_file', help='Path to the audio file')
    parser.add_argument('--output', help='Output JSON file path', default='transcription_results.json')
    
    args = parser.parse_args()
    
    # Check if the audio file exists
    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file '{args.audio_file}' not found")
        return
    
    # Get language preferences
    source_language, target_language = get_user_language_preferences()
    print(f"\nProcessing from {source_language['name']} to {target_language['name']}...")
    
    # Convert audio if needed
    wav_file = convert_audio_to_wav(args.audio_file)
    if not wav_file:
        print("Failed to convert audio file. Please check the format.")
        return
    
    # Transcribe
    original_text = transcribe_audio_with_whisper(wav_file, source_language['code'])
    print("\nOriginal Transcription:")
    print(original_text)
    
    # Clean up temp file
    if os.path.exists(wav_file):
        os.unlink(wav_file)
    
    # Translate
    if source_language['code'] != target_language['code']:
        translated_text = translate_text_simple(original_text, source_language['code'], target_language['code'])
        print(f"\nTranslated to {target_language['name']}:")
        print(translated_text)
    else:
        translated_text = original_text
        print("\nNo translation needed (same source and target language)")
    
    # Summarize
    summary = summarize_text_simple(translated_text)
    print(f"\nSummary in {target_language['name']}:")
    print(summary)
    
    # Save results
    save_results(original_text, translated_text, summary, args.output)

if __name__ == "__main__":
    main()
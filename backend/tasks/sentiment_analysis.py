import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import re
import json

import ssl
import urllib.request

ssl._create_default_https_context = ssl._create_unverified_context

nltk.download('vader_lexicon')

def read_conversation_from_file(filename):
    """Read conversation from a text file"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None

def analyze_conversation_sentiment(text):
    # Initialize sentiment analyzer
    sia = SentimentIntensityAnalyzer()
    
    # Split conversation by speaker
    speaker_pattern = re.compile(r'\[(Speaker_\d+)\]:\s*')
    speakers = {}
    
    # Parse the conversation
    current_speaker = None
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Check for speaker tag
        match = speaker_pattern.match(line)
        if match:
            current_speaker = match.group(1)
            line = speaker_pattern.sub('', line).strip()
            if current_speaker not in speakers:
                speakers[current_speaker] = []
        elif current_speaker:
            speakers[current_speaker].append(line)
    
    # Analyze sentiment per speaker
    results = {}
    for speaker, utterances in speakers.items():
        speaker_sentiments = []
        key_phrases = []
        
        for utterance in utterances:
            # Get sentiment scores
            scores = sia.polarity_scores(utterance)
            speaker_sentiments.append(scores['compound'])
            
            # Track significant phrases (positive/negative/neutral)
            if scores['compound'] >= 0.05:
                sentiment = 'positive'
            elif scores['compound'] <= -0.05:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            key_phrases.append({
                'text': utterance,
                'sentiment': sentiment,
                               'scores': {
                    'compound': round(scores['compound'], 4),
                    'positive': round(scores['pos'], 4),
                    'neutral': round(scores['neu'], 4),
                    'negative': round(scores['neg'], 4)
                }
            })
        
        # Calculate average sentiment
        avg_sentiment = sum(speaker_sentiments) / len(speaker_sentiments) if speaker_sentiments else 0
        
        # Determine overall sentiment label
        if avg_sentiment >= 0.05:
            overall_sentiment = 'positive'
        elif avg_sentiment <= -0.05:
            overall_sentiment = 'negative'
        else:
            overall_sentiment = 'neutral'
        
        results[speaker] = {
            'overall_sentiment': overall_sentiment,
            'average_compound': round(avg_sentiment, 4),
            'utterance_count': len(utterances),
            'detailed_analysis': key_phrases
        }
    
    return results

# Main execution
if __name__ == "__main__":
    input_file = "C:/ABHISHEKSUTARIA/projects/ai_meeting_assistant/meeting_analysis/meeting_analysis_20250405_214737/transcript/meeting_15mins_transcript_20250405_214910.txt"  # Input text file
    output_file = "C:/ABHISHEKSUTARIA/projects/ai_meeting_assistant/meeting_analysis/meeting_analysis_20250405_213456/sentiment/sentiment_results.json"  # Output JSON file
    
    # Read conversation from file
    conversation_text = read_conversation_from_file(input_file)
    
    if conversation_text:
        # Analyze sentiment
        results = analyze_conversation_sentiment(conversation_text)
        
        # Save to JSON file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved results to {output_file}")
        except Exception as e:
            print(f"Error saving JSON file: {str(e)}")
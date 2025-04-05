import os
import logging
from datetime import datetime
import json
import re
import nltk

nltk.data.path.append("/Users/yashwipassary/nltk_data")

from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Download NLTK resources if not already present
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

def summarize_meeting(transcript_text, output_dir="summaries", summary_ratio=0.3):
    """
    Generate a summary of the meeting transcript.
    
    Args:
        transcript_text (str): The transcript text to summarize
        output_dir (str): Directory to save the summary
        summary_ratio (float): Ratio of sentences to include in summary (0.1-0.5)
        
    Returns:
        dict: Dictionary containing the meeting summary details
        str: Path to the saved summary file
    """
    logger.info("Summarizing meeting transcript...")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
    
    # Tokenize the transcript into sentences
    sentences = sent_tokenize(transcript_text)
    
    # Extract meeting metadata
    metadata = extract_meeting_metadata(transcript_text)
    
    # Extract key topics
    topics = extract_key_topics(transcript_text)
    
    # Generate extractive summary
    summary_sentences = extractive_summarization(transcript_text, summary_ratio)
    summary = ' '.join(summary_sentences)
    
    # Create summary object
    meeting_summary = {
        "metadata": metadata,
        "key_topics": topics,
        "summary": summary,
        "full_transcript_length": len(transcript_text),
        "summary_length": len(summary),
        "compression_ratio": len(summary) / len(transcript_text) if len(transcript_text) > 0 else 0,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"meeting_summary_{timestamp}.json"
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(meeting_summary, f, indent=2)
    
    logger.info(f"Meeting summary saved to: {output_path}")
    
    return meeting_summary, output_path

def extract_meeting_metadata(transcript_text):
    """Extract metadata from the transcript text."""
    # Try to identify meeting date
    date_patterns = [
        r'(?:meeting|call|discussion)(?:\s+on|\s+of|\s+dated?|\s+held\s+on)?\s+([A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+,?\s+\d{4})'
    ]
    
    meeting_date = None
    for pattern in date_patterns:
        date_match = re.search(pattern, transcript_text)
        if date_match:
            meeting_date = date_match.group(1)
            break
    
    # Try to identify participants
    participants = []
    participant_pattern = r'(?:participants|attendees|present|joining)(?:[\s:]+)([^.]*)'
    participant_match = re.search(participant_pattern, transcript_text, re.IGNORECASE)
    
    if participant_match:
        participant_text = participant_match.group(1)
        # Split by common separators
        for separator in [',', ';', 'and']:
            if separator in participant_text:
                participants = [p.strip() for p in participant_text.split(separator) if p.strip()]
                break
    
    # Try to identify meeting title/subject
    title_patterns = [
        r'(?:meeting|call|discussion)\s+(?:about|on|regarding|re:|for)\s+([^.]*)',
        r'(?:title|subject|topic)(?:[\s:]+)([^.]*)',
        r'welcome\s+to\s+(?:the|our)?\s+([^.]*meeting|call|discussion)'
    ]
    
    title = None
    for pattern in title_patterns:
        title_match = re.search(pattern, transcript_text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            break
    
    # If no title found, use the first sentence as title (limited to 10 words)
    if not title:
        first_sentences = sent_tokenize(transcript_text)
        if first_sentences:
            title_words = first_sentences[0].split()[:10]
            title = ' '.join(title_words)
    
    return {
        "date": meeting_date,
        "participants": participants,
        "title": title,
    }

def extract_key_topics(transcript_text, num_topics=5):
    """Extract key topics from the transcript using word frequency."""
    # Tokenize and clean text
    words = word_tokenize(transcript_text.lower())
    stop_words = set(stopwords.words('english'))
    
    # Filter out stopwords and punctuation
    filtered_words = [word for word in words if word.isalpha() and word not in stop_words and len(word) > 3]
    
    # Find word frequency
    fdist = FreqDist(filtered_words)
    
    # Return top N most common words as topics
    return [word for word, freq in fdist.most_common(num_topics)]

def extractive_summarization(transcript_text, summary_ratio=0.3):
    """
    Perform extractive summarization by selecting important sentences.
    """
    # Tokenize text into sentences
    sentences = sent_tokenize(transcript_text)
    
    # If there are very few sentences, return them all
    if len(sentences) <= 3:
        return sentences
    
    # Tokenize and clean text for scoring
    words = word_tokenize(transcript_text.lower())
    stop_words = set(stopwords.words('english'))
    filtered_words = [word for word in words if word.isalpha() and word not in stop_words]
    
    # Calculate word frequency
    word_frequencies = FreqDist(filtered_words)
    
    # Calculate sentence scores based on word frequency
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        for word in word_tokenize(sentence.lower()):
            if word in word_frequencies:
                if i not in sentence_scores:
                    sentence_scores[i] = 0
                sentence_scores[i] += word_frequencies[word]
    
    # Normalize scores by sentence length to avoid bias towards long sentences
    for i in sentence_scores:
        sentence_scores[i] = sentence_scores[i] / max(1, len(word_tokenize(sentences[i])))
    
    # Determine how many sentences to include
    num_sentences = max(3, int(len(sentences) * summary_ratio))
    
    # Get indices of top scoring sentences
    top_indices = sorted(sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:num_sentences])
    
    # Return sentences in their original order
    return [sentences[i] for i in top_indices]

if __name__ == "__main__":
    # Example usage
    sample_transcript = """
    Meeting on January 15th, 2025: Q1 Planning Session
    
    Participants: Sarah Johnson, Michael Chen, Elena Rodriguez, and Thomas Wilson
    
    Sarah: Good morning everyone. Today we're discussing our Q1 objectives and key projects.
    
    Michael: I've prepared slides showing our current status. Revenue from last quarter exceeded expectations by 12%.
    
    Elena: That's great news. For this quarter, I believe we should focus on expanding the European market.
    
    Thomas: I agree with Elena. The market research indicates significant growth opportunities there.
    
    Sarah: Good point. We need to develop a comprehensive strategy for European expansion by the end of February.
    
    Michael: My team will be responsible for creating financial projections for the expansion.
    
    Elena: Marketing needs to analyze competitor positioning in each target country.
    
    Thomas: I will coordinate with our distribution partners to ensure we have the logistics in place.
    
    Sarah: Excellent. Let's schedule weekly check-ins to track our progress. Everyone should prepare status updates before each meeting.
    
    Michael: One more thing - we should discuss the new product launch timeline.
    
    Elena: According to R&D, the product will be ready for testing in March.
    
    Thomas: That seems ambitious. We need to ensure quality isn't compromised.
    
    Sarah: Agreed. Michael will work with R&D to review the timeline and make necessary adjustments.
    
    Meeting adjourned at 11:30 AM. Next meeting scheduled for January 22nd.
    """
    
    try:
        summary_results, file_path = summarize_meeting(sample_transcript)
        print(f"Meeting summary saved to: {file_path}")
        print(f"\nTitle: {summary_results['metadata']['title']}")
        print(f"Key topics: {', '.join(summary_results['key_topics'])}")
        print(f"\nSummary:\n{summary_results['summary']}")
    except Exception as e:
        print(f"Error: {str(e)}")
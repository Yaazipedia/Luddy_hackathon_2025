import re
import logging
from datetime import datetime
import json
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_action_items(transcript_text, output_dir="action_items"):
    """
    Extract action items from the transcript text.
    
    Args:
        transcript_text (str): The transcript text to analyze
        output_dir (str): Directory to save the action items
        
    Returns:
        list: List of dictionaries containing action items
        str: Path to the saved action items file
    """
    logger.info("Extracting action items from transcript...")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
    
    # Patterns to identify action items
    patterns = [
        r"(?:need to|must|should|will|going to|have to|assigned to|responsible for)\s+([^.!?]+)",
        r"action item[s]?:?\s+([^.!?]+)",
        r"task[s]? for\s+([^.!?]+)",
        r"(?:follow[ -]up|follow up)[s]?:?\s+([^.!?]+)",
        r"(?:[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:will|should|needs to)\s+([^.!?]+)"
    ]
    
    action_items = []
    
    # Parse transcript to find action items
    for pattern in patterns:
        matches = re.finditer(pattern, transcript_text, re.IGNORECASE)
        for match in matches:
            # Extract the full match and clean it
            full_match = match.group(0).strip()
            
            # Find the sentence containing this match
            sentence_pattern = r'[.!?]\s+[A-Z]'
            sentences = re.split(sentence_pattern, transcript_text)
            containing_sentence = ""
            
            for sentence in sentences:
                if full_match in sentence:
                    containing_sentence = sentence.strip()
                    break
            
            # Try to extract the person responsible
            person_match = re.search(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:will|should|needs to|has to|is going to)', full_match)
            person = person_match.group(1) if person_match else "Unassigned"
            
            # Create action item object
            action_item = {
                "action": full_match,
                "context": containing_sentence if containing_sentence else full_match,
                "assigned_to": person,
                "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            action_items.append(action_item)
    
    # Remove duplicates while preserving order
    unique_actions = []
    seen_actions = set()
    for item in action_items:
        if item["action"] not in seen_actions:
            unique_actions.append(item)
            seen_actions.add(item["action"])
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"action_items_{timestamp}.json"
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(unique_actions, f, indent=2)
    
    logger.info(f"Extracted {len(unique_actions)} action items")
    logger.info(f"Action items saved to: {output_path}")
    
    return unique_actions, output_path

if __name__ == "__main__":
    # Example usage
    sample_transcript = """
    In today's meeting, we discussed the Q3 results. John will prepare the financial report by Friday.
    Sarah needs to contact the marketing team about the new campaign launch.
    Action item: Everyone should review the product roadmap before next week's meeting.
    Tom is responsible for coordinating with the development team on the bug fixes.
    We need to schedule a follow-up meeting with the client next month.
    """
    
    try:
        items, file_path = extract_action_items(sample_transcript)
        print(f"Action items saved to: {file_path}")
        for i, item in enumerate(items, 1):
            print(f"\nItem {i}:")
            print(f"Action: {item['action']}")
            print(f"Assigned to: {item['assigned_to']}")
    except Exception as e:
        print(f"Error: {str(e)}")
import os
import sys
import logging
import json
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud
import re

# Import the other modules
from process_audio import process_audio
from extract_items import extract_action_items
from summarize_meeting import summarize_meeting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meeting_analysis.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def analyze_meeting(audio_file_path, output_dir="meeting_analysis"):
    """
    Complete pipeline to process audio, extract action items, and summarize a meeting.
    
    Args:
        audio_file_path (str): Path to the audio file
        output_dir (str): Directory to save all outputs
        
    Returns:
        dict: Analysis results with paths to all generated files
    """
    logger.info(f"Starting analysis of meeting audio: {audio_file_path}")
    
    # Create main output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
    
    # Create timestamp for this analysis run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_id = f"meeting_analysis_{timestamp}"
    
    # Create specific output directory for this analysis
    analysis_dir = os.path.join(output_dir, analysis_id)
    os.makedirs(analysis_dir)
    
    result = {
        "analysis_id": analysis_id,
        "audio_file": audio_file_path,
        "timestamp": timestamp,
        "output_directory": analysis_dir
    }
    
    try:
        # Step 1: Process audio to text
        transcript_dir = os.path.join(analysis_dir, "transcript")
        os.makedirs(transcript_dir)
        transcript_path, transcript_text = process_audio(audio_file_path, transcript_dir)
        result["transcript_path"] = transcript_path
        
        # Step 2: Extract action items
        action_items_dir = os.path.join(analysis_dir, "action_items")
        os.makedirs(action_items_dir)
        action_items, action_items_path = extract_action_items(transcript_text, action_items_dir)
        result["action_items_path"] = action_items_path
        result["action_items_count"] = len(action_items)
        
        # Step 3: Summarize meeting
        summary_dir = os.path.join(analysis_dir, "summary")
        os.makedirs(summary_dir)
        summary, summary_path = summarize_meeting(transcript_text, summary_dir)
        result["summary_path"] = summary_path
        
        # Step 4: Generate visualizations
        visualizations_dir = os.path.join(analysis_dir, "visualizations")
        os.makedirs(visualizations_dir)
        
        viz_results = generate_visualizations(
            transcript_text, 
            action_items, 
            summary, 
            visualizations_dir
        )
        result["visualizations"] = viz_results
        
        # Step 5: Generate final report
        report = generate_report(result, transcript_text, action_items, summary)
        report_path = os.path.join(analysis_dir, "meeting_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        result["report_path"] = report_path
        
        logger.info(f"Meeting analysis completed successfully. Results saved to: {analysis_dir}")
        return result
    
    except Exception as e:
        logger.error(f"Error during meeting analysis: {str(e)}")
        error_report = {
            "error": str(e),
            "stage": result.get("transcript_path", "Unknown"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        error_path = os.path.join(analysis_dir, "error_report.json")
        with open(error_path, 'w', encoding='utf-8') as f:
            json.dump(error_report, f, indent=2)
        raise

def generate_visualizations(transcript_text, action_items, summary, output_dir):
    """Generate visualizations from the meeting data."""
    logger.info("Generating visualizations...")
    visualization_paths = {}
    
    # 1. Word cloud of the transcript
    try:
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(transcript_text)
        wordcloud_path = os.path.join(output_dir, "transcript_wordcloud.png")
        wordcloud.to_file(wordcloud_path)
        visualization_paths["wordcloud"] = wordcloud_path
    except Exception as e:
        logger.warning(f"Failed to generate word cloud: {str(e)}")
    
    # 2. Action items by assignee
    try:
        assignees = {}
        for item in action_items:
            assignee = item.get("assigned_to", "Unassigned")
            assignees[assignee] = assignees.get(assignee, 0) + 1
        
        # Create bar chart
        plt.figure(figsize=(10, 6))
        names = list(assignees.keys())
        counts = list(assignees.values())
        plt.bar(names, counts)
        plt.xlabel('Assignee')
        plt.ylabel('Number of Action Items')
        plt.title('Action Items by Assignee')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        action_items_chart_path = os.path.join(output_dir, "action_items_by_assignee.png")
        plt.savefig(action_items_chart_path)
        plt.close()
        visualization_paths["action_items_chart"] = action_items_chart_path
    except Exception as e:
        logger.warning(f"Failed to generate action items chart: {str(e)}")
    
    # 3. Topic distribution pie chart
    try:
        topics = summary.get("key_topics", [])
        if topics:
            # Count occurrences of each topic in the transcript
            topic_counts = {}
            for topic in topics:
                pattern = r'\b' + re.escape(topic) + r'\b'
                count = len(re.findall(pattern, transcript_text, re.IGNORECASE))
                topic_counts[topic] = max(1, count)  # Ensure at least 1 count
            
            # Create pie chart
            plt.figure(figsize=(8, 8))
            labels = list(topic_counts.keys())
            sizes = list(topic_counts.values())
            plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('Topic Distribution')
            
            topics_chart_path = os.path.join(output_dir, "topic_distribution.png")
            plt.savefig(topics_chart_path)
            plt.close()
            visualization_paths["topics_chart"] = topics_chart_path
    except Exception as e:
        logger.warning(f"Failed to generate topic distribution chart: {str(e)}")
    
    return visualization_paths

def generate_report(result, transcript_text, action_items, summary):
    """Generate a comprehensive report from all analysis components."""
    logger.info("Generating final report...")
    
    # Analyze the transcript for some basic metrics
    word_count = len(transcript_text.split())
    sentence_patterns = [r'\.', r'\?', r'!']
    sentence_count = 0
    for pattern in sentence_patterns:
        sentence_count += len(re.findall(pattern, transcript_text))
    
    # Extract key metrics from summary
    key_topics = summary.get("key_topics", [])
    metadata = summary.get("metadata", {})
    
    # Build final report
    report = {
        "analysis_id": result["analysis_id"],
        "timestamp": result["timestamp"],
        "audio_source": result["audio_file"],
        "transcript_statistics": {
            "word_count": word_count,
            "estimated_sentence_count": sentence_count,
            "transcript_path": result["transcript_path"]
        },
        "meeting_details": {
            "title": metadata.get("title", "Unknown"),
            "date": metadata.get("date", "Unknown"),
            "participants": metadata.get("participants", []),
        },
        "key_topics": key_topics,
        "summary": summary.get("summary", ""),
        "action_items": {
            "count": len(action_items),
            "items": action_items,
            "action_items_path": result["action_items_path"]
        },
        "output_files": {
            "transcript": result["transcript_path"],
            "summary": result["summary_path"],
            "action_items": result["action_items_path"],
            "visualizations": result.get("visualizations", {})
        }
    }
    
    return report

def main():
    """Main function to run the meeting analysis CLI."""
    parser = argparse.ArgumentParser(description='Analyze meeting audio recordings')
    parser.add_argument('audio_file', help='Path to the meeting audio file')
    parser.add_argument('--output-dir', default='meeting_analysis', help='Directory to save analysis outputs')
    
    args = parser.parse_args()
    
    try:
        results = analyze_meeting(args.audio_file, args.output_dir)
        print(f"\nAnalysis completed successfully!")
        print(f"Results saved to: {results['output_directory']}")
        print(f"Report file: {results['report_path']}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
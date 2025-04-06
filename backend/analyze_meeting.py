import os
import sys
import logging
import json
import argparse
from datetime import datetime
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud
import re

matplotlib.use('Agg')

# Import the other modules
from tasks.process_audio import process_audio
from tasks.extract_items import extract_action_items
from tasks.summarize_meeting import summarize_meeting
from tasks.sentiment_analysis import analyze_conversation_sentiment, read_conversation_from_file


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
    logger.info(f"Starting analysis of meeting audio: {audio_file_path}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_id = f"meeting_analysis_{timestamp}"
    analysis_dir = os.path.join(output_dir, analysis_id)
    os.makedirs(analysis_dir)

    result = {
        "analysis_id": analysis_id,
        "audio_file": audio_file_path,
        "timestamp": timestamp,
        "output_directory": analysis_dir
    }

    try:
        transcript_dir = os.path.join(analysis_dir, "transcript")
        os.makedirs(transcript_dir)
        transcript_path, transcript_text = process_audio(audio_file_path, transcript_dir)
        result["transcript_path"] = transcript_path

        action_items_dir = os.path.join(analysis_dir, "action_items")
        os.makedirs(action_items_dir)
        action_items, action_items_path = extract_action_items(transcript_text, action_items_dir)
        result["action_items_path"] = action_items_path
        result["action_items_count"] = len(action_items)

        summary_dir = os.path.join(analysis_dir, "summary")
        os.makedirs(summary_dir)
        summary, summary_path = summarize_meeting(transcript_text, summary_dir)
        result["summary_path"] = summary_path

        sentiment_results = None  # Initialize before visualizations

        visualizations_dir = os.path.join(analysis_dir, "visualizations")
        os.makedirs(visualizations_dir)

        sentiment_dir = os.path.join(analysis_dir, "sentiment")
        os.makedirs(sentiment_dir, exist_ok=True)
        sentiment_output_path = os.path.join(sentiment_dir, "sentiment_results.json")

        logger.info("Running sentiment analysis on transcript...")
        conversation_text = read_conversation_from_file(transcript_path)
        if conversation_text:
            sentiment_results = analyze_conversation_sentiment(conversation_text)
            with open(sentiment_output_path, 'w', encoding='utf-8') as f:
                json.dump(sentiment_results, f, indent=2, ensure_ascii=False)
            result["sentiment_path"] = sentiment_output_path
            result["sentiment_summary"] = {
                speaker: {
                    "overall_sentiment": data["overall_sentiment"],
                    "average_compound": data["average_compound"]
                }
                for speaker, data in sentiment_results.items()
            }
            logger.info(f"Sentiment analysis results saved to: {sentiment_output_path}")
        else:
            logger.warning("Transcript could not be read for sentiment analysis.")

        viz_results = generate_visualizations(
            transcript_text,
            action_items,
            summary,
            visualizations_dir,
            sentiment_results=sentiment_results
        )
        result["visualizations"] = viz_results

        report = generate_report(result, transcript_text, action_items, summary, sentiment_results)
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

def generate_visualizations(transcript_text, action_items, summary, output_dir, sentiment_results=None):
    logger.info("Generating visualizations...")
    visualization_paths = {}

    try:
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(transcript_text)
        wordcloud_path = os.path.join(output_dir, "transcript_wordcloud.png")
        wordcloud.to_file(wordcloud_path)
        visualization_paths["wordcloud"] = wordcloud_path
    except Exception as e:
        logger.warning(f"Failed to generate word cloud: {str(e)}")

    try:
        assignees = {}
        for item in action_items:
            assignee = item.get("assigned_to", "Unassigned")
            assignees[assignee] = assignees.get(assignee, 0) + 1

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

    try:
        topics = summary.get("key_topics", [])
        if topics:
            topic_counts = {}
            for topic in topics:
                pattern = r'\b' + re.escape(topic) + r'\b'
                count = len(re.findall(pattern, transcript_text, re.IGNORECASE))
                topic_counts[topic] = max(1, count)

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

    try:
        if sentiment_results:
            sentiments_by_speaker = {
                speaker: data["overall_sentiment"]
                for speaker, data in sentiment_results.items()
            }
            sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
            for s in sentiments_by_speaker.values():
                sentiment_counts[s] = sentiment_counts.get(s, 0) + 1

            plt.figure(figsize=(8, 6))
            bars = plt.bar(sentiment_counts.keys(), sentiment_counts.values())
            plt.title("Overall Sentiment by Speaker")
            plt.xlabel("Sentiment")
            plt.ylabel("Number of Speakers")
            plt.tight_layout()

            sentiment_chart_path = os.path.join(output_dir, "sentiment_distribution.png")
            plt.savefig(sentiment_chart_path)
            plt.close()
            visualization_paths["sentiment_chart"] = sentiment_chart_path
    except Exception as e:
        logger.warning(f"Failed to generate sentiment chart: {str(e)}")

    return visualization_paths

def generate_report(result, transcript_text, action_items, summary, sentiment_results=None):
    logger.info("Generating final report...")

    word_count = len(transcript_text.split())
    sentence_patterns = [r'\.', r'\?', r'!']
    sentence_count = 0
    for pattern in sentence_patterns:
        sentence_count += len(re.findall(pattern, transcript_text))

    key_topics = summary.get("key_topics", [])
    metadata = summary.get("metadata", {})

    report = {
        "analysis_id": result["analysis_id"],
        "timestamp": result["timestamp"],
        "audio_source": result["audio_file"],
        "sentiment_analysis": sentiment_results if sentiment_results else "Not available",
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
    start_time = datetime.now()
    main()
    end_time = datetime.now()
    print(f"Execution time = {end_time - start_time}")
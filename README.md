# Luddy_hackathon_2025
# MeetSmart - AI-Powered Meeting Companion

## Overview
This AI-powered assistant transcribes, summarizes, and analyzes meetings in both real-time and from recorded files. It helps teams quickly understand discussions, identify action items, analyze sentiment, and extract key information from meetings across multiple languages.

## Features
- **Audio Transcription**: Process live audio streams and uploaded audio/video files
- **Intelligent Summarization**: Generate concise TL;DRs and bullet-point summaries
- **Action Item Extraction**: Automatically identify tasks, owners, and deadlines
- **Sentiment Analysis**: Analyze tone and emotion per speaker or segment
- **Multi-language Support**: Process and analyze meetings in various languages
- **Real-time Processing**: Live transcription and analysis during ongoing meetings
- **Email Distribution**: Automatically send meeting summaries to participants or manually specified recipients
- **Data Visualization**: Interactive visualizations of meeting data including word clouds, sentiment distribution, and action item assignment

## Project Structure
```
.
├── backend/                              # Core application code
│   ├── tasks/                   # Python cache directory
│       ├── email_summary.py               # Email generation for meeting summaries
│       ├── extract_items.py               # Extract action items and decisions
│       ├── multi_language_summary.py      # Multi-language support for summaries
│       ├── process_audio.py               # Audio processing pipeline
│       ├── process_audio_original.py      # Original audio processing implementation
│       ├── realtime_meeting.py            # Real-time meeting transcription
│       ├── recorder.py                    # Audio recording functionality
│       ├── sentiment_analysis.py          # Sentiment and tone analysis
│       └── summarize_meeting.py           # Meeting summarization algorithms
│   ├── analyze_meeting.py/                # Python Functions driver code
│   ├── main.py/                           # FastAPI driver code
├── meeting_analysis/                  # Analysis outputs and utilities
│   ├── meeting_analysis_[TIMESTAMP]/  # Timestamped analysis for each meeting
│   │   ├── action_items/              # Extracted action items
│   │   ├── sentiment/                 # Sentiment analysis data
│   │   ├── summary/                   # Meeting summaries
│   │   ├── transcript/                # Full meeting transcript
│   │   ├── visualizations/            # Visual representations of meeting data
│   │   │   ├── action_items_by_assignee.png  # Action items distribution chart
│   │   │   ├── sentiment_distribution.png    # Sentiment analysis visualization
│   │   │   ├── topic_distribution.png        # Topic distribution chart
│   │   │   └── transcript_wordcloud.png      # Word cloud from transcript
│   │   └── meeting_report.json        # Complete meeting analysis in JSON format
├── meeting_recordings/                # Storage for meeting recordings
├── realtime_meetings/                 # Real-time meeting data
├── .DS_Store                          # MacOS system file
├── README.md                          # Project documentation
├── meeting_15mins.mp4                 # Sample meeting recording
└── meeting_analysis.log               # Analysis log file
```

## Core Components

### Audio Processing
- **recorder.py** -  Live transcription and processing of ongoing meetings
- **process_audio.py** - Processes audio files for transcription
- **process_audio_original.py** - Original version of audio processing

### Transcription & Analysis
- **realtime_meeting.py** - Handles audio capture from microphone input
- **analyze_meeting.py** - Comprehensive meeting analysis and visualization
- **sentiment_analysis.py** - Analyze emotional tone throughout the meeting

### Summary Generation
- **summarize_meeting.py** - Creates concise meeting summaries
- **email_summary.py** - Formats and sends meeting summaries via email to participants or manually added recipients
- **multi_language_summary.py** - Generates summaries in multiple languages

### Data Extraction
- **extract_items.py** - Identifies and extracts action items, decisions, and key points

## Installation

```bash
# Clone the repository
git clone https://github.com/YashwiPassary/Luddy_hackathon_2025.git
cd Luddy_hackathon_2025

# Set up virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Processing a Recorded Meeting
```python
from code.process_audio import process_audio_file
from code.summarize_meeting import generate_summary
from code.extract_items import extract_action_items
from code.sentiment_analysis import analyze_sentiment

# Process a meeting recording
transcript = process_audio_file("meeting_recordings/meeting_15mins.mp4")

# Generate summary
summary = generate_summary(transcript)

# Extract action items
action_items = extract_action_items(transcript)

# Analyze sentiment
sentiment_data = analyze_sentiment(transcript)

# Print results
print("Meeting Summary:")
print(summary)
print("\nAction Items:")
for item in action_items:
    print(f"- {item}")
```

### Real-time Meeting Analysis
```python
from code.realtime_meeting import RealtimeMeeting
from code.recorder import AudioRecorder

# Start a new real-time meeting session
recorder = AudioRecorder()
meeting = RealtimeMeeting()

# Begin recording and processing
recorder.start()
meeting.start_processing()

# When meeting is finished
recorder.stop()
meeting.stop_processing()

# Get meeting insights
summary = meeting.get_summary()
action_items = meeting.get_action_items()
sentiment = meeting.get_sentiment_analysis()
```

### Sending Meeting Summaries via Email
The system provides two ways to distribute meeting summaries via email:

1. **Automatic Distribution**: Meeting summaries can be automatically sent to all participants detected in the meeting.
   
2. **Manual Recipients**: Users can manually specify recipient email addresses to receive the meeting summary, transcription, and analysis reports.

The email includes:
- Meeting summary with key points
- Complete or partial transcription
- Action items with assignees and deadlines
- Sentiment analysis overview
- Links to full analysis (if hosted)

Email distribution can be configured in the web dashboard or triggered programmatically.

## Web Dashboard
```
<img width="1514" alt="image" src="https://github.com/user-attachments/assets/c69467bb-33d2-4bfd-b44a-ddd42848ea57" />
```

The project includes a web dashboard for visualizing meeting data, including:
- Live transcription feed
- Meeting summaries
- Action item tracking
- Sentiment analysis visualization
- Language detection and translation options
- Email distribution management for meeting summaries
- Visualization Dashboard that captures word clouds, sentiment distribution, and action item assignment

```
<img width="1586" alt="image" src="https://github.com/user-attachments/assets/e2074667-6fdd-4c2b-92ef-e56d51c02c0f" />

```

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

[MIT License](LICENSE)

## Acknowledgments

- Speech recognition powered by OpenAI Whisper
- NLP processing using NLTK
- Sentiment analysis using NLTK.sentiment
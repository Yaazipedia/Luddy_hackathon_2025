import os
import json
import sys
import smtplib
import logging
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_email_content(report_data, transcript_path, action_items_path, summary_path):
    """
    Format the email content with meeting summary and key points.
    
    Args:
        report_data (dict): Meeting report data
        transcript_path (str): Path to transcript file
        action_items_path (str): Path to action items file
        summary_path (str): Path to summary file
        
    Returns:
        str: HTML content for the email
    """
    # Load data files
    action_items = []
    summary_content = {}
    
    try:
        with open(action_items_path, 'r', encoding='utf-8') as f:
            action_items = json.load(f)
    except Exception as e:
        logger.error(f"Error loading action items: {str(e)}")
    
    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary_content = json.load(f)
    except Exception as e:
        logger.error(f"Error loading summary: {str(e)}")
    
    # Format the email HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #0066cc; }}
            h2 {{ color: #444; margin-top: 20px; }}
            .topic-list {{ display: flex; flex-wrap: wrap; margin-bottom: 15px; }}
            .topic-item {{ background: #e6f2ff; padding: 5px 10px; margin: 3px; border-radius: 3px; }}
            .action-item {{ margin-bottom: 10px; padding-left: 20px; border-left: 3px solid #0066cc; }}
            .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Meeting Summary</h1>
            <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
    """
    
    # Add meeting title if available
    if summary_content.get("metadata", {}).get("title"):
        html_content += f"""
            <p><strong>Meeting Title:</strong> {summary_content["metadata"]["title"]}</p>
        """
    
    # Add key topics
    key_topics = summary_content.get("key_topics", []) or report_data.get("key_topics", [])
    if key_topics:
        html_content += f"""
            <h2>Key Topics</h2>
            <div class="topic-list">
        """
        for topic in key_topics:
            html_content += f'<div class="topic-item">{topic}</div>'
        html_content += "</div>"
    
    # Add summary
    if summary_content.get("summary"):
        html_content += f"""
            <h2>Meeting Summary</h2>
            <p>{summary_content["summary"]}</p>
        """
    
    # Add action items
    if action_items:
        html_content += """
            <h2>Action Items</h2>
        """
        for i, item in enumerate(action_items, 1):
            assignee = item.get("assigned_to", "Unassigned")
            action = item.get("action", "")
            html_content += f"""
            <div class="action-item">
                <p><strong>Item {i}:</strong> {action}</p>
                <p><strong>Assigned to:</strong> {assignee}</p>
            </div>
            """
    
    # Add footer
    html_content += f"""
            <div class="footer">
                <p>This email was automatically generated based on the meeting recording.</p>
                <p>Full transcript and detailed analysis available upon request.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def send_meeting_summary(report_path, recipients, smtp_server, smtp_port, sender_email, sender_password):
    """
    Send meeting summary email to attendees.
    
    Args:
        report_path (str): Path to the meeting report file
        recipients (list): List of email addresses to send to
        smtp_server (str): SMTP server address
        smtp_port (int): SMTP server port
        sender_email (str): Sender's email address
        sender_password (str): Sender's email password
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Load report data
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # Get file paths from report
        transcript_path = report_data.get("transcript_file", "")
        action_items_path = report_data.get("action_items_file", "")
        summary_path = report_data.get("summary_file", "")
        
        # Prepare email content
        html_content = format_email_content(report_data, transcript_path, action_items_path, summary_path)
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipients)
        
        # Set email subject
        meeting_title = "Meeting Summary"
        if report_data.get("meeting_title"):
            meeting_title = f"Summary: {report_data['meeting_title']}"
        msg['Subject'] = meeting_title
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Optionally attach the transcript file
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_attachment = MIMEText(f.read())
                transcript_attachment.add_header('Content-Disposition', 'attachment', 
                                              filename=os.path.basename(transcript_path))
                msg.attach(transcript_attachment)
        
        # Connect to SMTP server and send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS encryption
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Meeting summary email sent to {len(recipients)} recipients")
        return True
        
    except Exception as e:
        logger.error(f"Error sending meeting summary email: {str(e)}")
        return False

def main():
    """Main function to send meeting summary email."""
    parser = argparse.ArgumentParser(description='Send meeting summary email to attendees')
    parser.add_argument('report_path', help='Path to the meeting report JSON file')
    parser.add_argument('--recipients', required=True, nargs='+', help='Email addresses of recipients')
    parser.add_argument('--smtp-server', required=True, help='SMTP server address')
    parser.add_argument('--smtp-port', type=int, default=587, help='SMTP server port')
    parser.add_argument('--sender-email', required=True, help='Sender email address')
    parser.add_argument('--sender-password', required=True, help='Sender email password')
    
    args = parser.parse_args()
    
    success = send_meeting_summary(
        args.report_path,
        args.recipients,
        args.smtp_server,
        args.smtp_port,
        args.sender_email,
        args.sender_password
    )
    
    if success:
        print(f"Meeting summary email sent successfully to {len(args.recipients)} recipients")
    else:
        print("Failed to send meeting summary email. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
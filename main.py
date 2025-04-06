from datetime import datetime
import glob
import shutil
import os
import json
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel, EmailStr
from analyze_meeting import analyze_meeting
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from tasks.email_summary import send_meeting_summary

app = FastAPI()

# Allow all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class FilePathRequest(BaseModel):
    file_path: str

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/process-audio-file")
def process(audio_file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, audio_file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(audio_file.file, buffer)
    return analyze_meeting(file_location)

@app.post("/read-file")
async def read_file(request: FilePathRequest):
    file_path = request.file_path

    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Determine file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # Handle supported image types
    image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
    if ext in image_extensions:
        return FileResponse(file_path, media_type=f"image/{ext.strip('.')}", filename=os.path.basename(file_path))

    # Handle supported text and JSON
    if ext in [".txt", ".json"]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if ext == ".json":
                    content = json.load(f)
                else:
                    content = f.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
        return JSONResponse(content={"file_path": file_path, "content": content})

    # Unsupported file type
    raise HTTPException(status_code=400, detail="Unsupported file type")

def extract_datetime_from_dirname(dirname: str) -> datetime:
    """
    Extracts and parses datetime from a folder name like 'meeting_analysis_20250406_013031'
    """
    timestamp_str = dirname.replace("meeting_analysis_", "")
    return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

def get_latest_meeting_report_dir(base_dir="meeting_analysis") -> str:
    """
    Scans the meeting_analysis folder and returns the latest directory by timestamp
    """
    dirs = [
        os.path.join(base_dir, d)
        for d in os.listdir(base_dir)
        if d.startswith("meeting_analysis_") and os.path.isdir(os.path.join(base_dir, d))
    ]

    if not dirs:
        raise FileNotFoundError("No meeting_analysis directories found.")

    # Sort by extracted datetime
    latest_dir = max(dirs, key=lambda d: extract_datetime_from_dirname(os.path.basename(d)))
    return latest_dir

class EmailRequest(BaseModel):
    recipients: List[EmailStr]

@app.post("/send-latest-report")
async def send_latest_meeting_report(request: EmailRequest):
    # 1. Locate the latest report JSON in the meeting_analysis folder
    report_dirs = glob.glob("meeting_analysis/*/")
    if not report_dirs:
        raise HTTPException(status_code=404, detail="No meeting_analysis directories found.")

    # Sort directories by modified time (descending)
    latest_dir = get_latest_meeting_report_dir()

    report_path = os.path.join(latest_dir, "meeting_report.json")
    print(report_path)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="report.json not found in latest directory.")

    # 2. Load your email config (can be from env or a config file)
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("SENDER_EMAIL", "ypassary.masters@gmail.com")
    sender_password = os.getenv("SENDER_PASSWORD", "xorl doqf cbyn egvz")  # Should be secret

    # 3. Send the email
    success = send_meeting_summary(
        report_path=report_path,
        recipients=request.recipients,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        sender_email=sender_email,
        sender_password=sender_password
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email.")

    return {"message": "Meeting summary sent successfully", "recipients": request.recipients}

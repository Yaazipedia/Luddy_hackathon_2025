import whisper
import spacy
import os
import pandas as pd
import json

def transcribe_audio(file_path):
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result["text"]

def extract_tasks(text):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)

    task_keywords = ["need to", "should", "must", "have to", "make sure", "let’s", "we will", "we’ll", "remember to", "don’t forget"]
    tasks = []

    for sent in doc.sents:
        s = sent.text.strip()
        if any(keyword in s.lower() for keyword in task_keywords):
            tasks.append(f"• {s}")

    return tasks

def save_tasks(tasks, filename_base):
    # Save to JSON
    with open(f"{filename_base}_tasks.json", "w") as json_file:
        json.dump(tasks, json_file, indent=4)

    # Save to CSV
    df = pd.DataFrame(tasks, columns=["Task"])
    df.to_csv(f"{filename_base}_tasks.csv", index=False)

    print(f"Tasks saved to {filename_base}_tasks.json and {filename_base}_tasks.csv")

def process_audio_to_tasks(file_path):
    print(f"Processing file: {file_path}")
    base_filename = os.path.splitext(os.path.basename(file_path))[0]

    transcript = transcribe_audio(file_path)
    print("\n📝 Transcription:\n", transcript[:500], "...\n")  # Print first 500 characters

    tasks = extract_tasks(transcript)

    if tasks:
        print("\n✅ Extracted Tasks:")
        for task in tasks:
            print(task)
    else:
        print("\n❌ No tasks found.")

    save_tasks(tasks, base_filename)

# --- Run it ---
if __name__ == "__main__":
    input_file = "/Users/yashwipassary/Downloads/hackathon/test_file.mp4"  # Replace with your .mp3 or .mp4 file path
    process_audio_to_tasks(input_file)

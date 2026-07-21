import os
import json
import re
import asyncio
import glob
import requests
import yt_dlp
import edge_tts
from google import genai

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not CHAT_ID or not GEMINI_KEY:
    raise ValueError("Missing one or more required Secrets: GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, or TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_KEY)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})
    if res.status_code != 200:
        print(f"Telegram Message Error: {res.text}")

def send_telegram_file(file_path, endpoint="sendDocument", caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{endpoint}"
    file_key = "video" if endpoint == "sendVideo" else "document"
    with open(file_path, "rb") as f:
        res = requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={file_key: f})
        if res.status_code != 200:
            print(f"Telegram File Upload Error ({endpoint}): {res.text}")

def clean_json_response(text):
    """Safely extracts raw JSON from Gemini markdown output."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text

async def run_pipeline():
    print("1. Querying Gemini API...")
    prompt = """
    Give me a viral sports concept for YouTube Shorts.
    Return strictly JSON without markdown wrappers:
    {
        "title": "Short Title",
        "script": "Fast 40-word commentary narration script.",
        "search_term": "curry clutch shots",
        "instructions": "Clip 1 (0-3s): Highlight. Clip 2 (3-7s): Reaction. Overlay: [TEXT]"
    }
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    clean_json = clean_json_response(response.text)
    data = json.loads(clean_json)
    
    msg = f"🚀 *NEW SHORTS PACKAGE: {data['title']}*\n\n"
    msg += f"📝 *SCRIPT:*\n{data['script']}\n\n"
    msg += f"🎬 *EDIT BLUEPRINT:*\n{data['instructions']}"
    send_telegram_message(msg)

    print("2. Generating Audio Commentary...")
    audio_path = "commentary.mp3"
    communicate = edge_tts.Communicate(data["script"], "en-US-ChristopherNeural")
    await communicate.save(audio_path)
    send_telegram_file(audio_path, endpoint="sendDocument", caption="🎙️ Voiceover Audio")

    print("✅ Finished sending instructions and audio!")

if __name__ == "__main__":
    asyncio.run(run_pipeline())

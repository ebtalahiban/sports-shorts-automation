import os
import json
import asyncio
import requests
import yt_dlp
import edge_tts
from google import genai

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def send_telegram_document(file_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"document": f})

async def run_pipeline():
    # 1. Generate Concept & Script via Gemini
    prompt = """
    Give me a high-energy viral sports concept for YouTube Shorts.
    Return strictly JSON:
    {
        "title": "short_title",
        "script": "Fast 40-word narration commentary.",
        "search_term": "TikTok search keyword for clips",
        "instructions": "Clip 1: 0-3s highlight. Clip 2: 3-7s reaction. Overlay text: [TEXT]"
    }
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    data = json.loads(response.text.strip('```json').strip('```'))
    
    # Send instructions to Telegram
    msg = f"🚀 *NEW SHORTS PACKAGE: {data['title']}*\n\n"
    msg += f"📝 *SCRIPT:*\n{data['script']}\n\n"
    msg += f"🎬 *EDIT BLUEPRINT:*\n{data['instructions']}"
    send_telegram_message(msg)

    # 2. Generate Audio via Edge-TTS
    audio_path = "commentary.mp3"
    communicate = edge_tts.Communicate(data["script"], "en-US-ChristopherNeural")
    await communicate.save(audio_path)
    send_telegram_document(audio_path, caption="🎙️ Voiceover Audio")

if __name__ == "__main__":
    asyncio.run(run_pipeline())

import os
import json
import re
import asyncio
import glob
import requests
import yt_dlp
import edge_tts

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not BOT_TOKEN or not CHAT_ID or not OPENROUTER_KEY:
    raise ValueError("Missing Secrets: OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN, or TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def send_telegram_file(file_path, endpoint="sendDocument", caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{endpoint}"
    file_key = "video" if endpoint == "sendVideo" else "document"
    with open(file_path, "rb") as f:
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={file_key: f})

def clean_json_response(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text

async def run_pipeline():
    print("1. Querying Qwen via OpenRouter...")
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
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openrouter/free",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions", 
        headers=headers, 
        json=payload
    )
    
    response_data = response.json()
    
    # --- ADD THIS NEW ERROR HANDLING ---
    if 'choices' not in response_data:
        print("❌ OPENROUTER API ERROR:")
        print(json.dumps(response_data, indent=2))
        raise ValueError("OpenRouter request failed. Check the logs above for details.")
    # -----------------------------------
        
    raw_text = response_data['choices'][0]['message']['content']
    
    clean_json = clean_json_response(raw_text)
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

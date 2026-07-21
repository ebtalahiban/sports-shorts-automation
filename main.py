import os
import json
import re
import asyncio
import glob
import requests
import yt_dlp

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not BOT_TOKEN or not CHAT_ID or not OPENROUTER_KEY:
    raise ValueError("Missing Secrets: OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN, or TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def send_telegram_video(file_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(file_path, "rb") as f:
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"video": f})

def clean_json_response(text):
    # Strip markdown wrappers
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0).strip()
    return text.strip()

def download_vertical_clips(search_term, output_dir="downloaded_clips", max_clips=5):
    """Searches and downloads vertical shorts automatically."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Search for 15 clips to build a buffer in case some get blocked by bot-detection
    search_query = f"ytsearch15:{search_term} shorts vertical"
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1920]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{output_dir}/clip_%(autonumber)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,         # Skip blocked videos instead of crashing
        'max_downloads': max_clips,   # Stop downloading once we successfully hit the limit
    }
    
    print(f"Attempting to download {max_clips} clips for query: {search_term}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([search_query])

async def run_pipeline():
    print("1. Querying AI via OpenRouter...")
    prompt = """
    Give me a viral sports concept for a 9:16 vertical short video using 5 fast-paced clips.
    Return strictly JSON without markdown wrappers:
    {
        "title": "Short Title",
        "search_term": "curry clutch shots",
        "instructions": "Clip 1 (0-2s): Hook. Clip 2 (2-4s): Build-up. Clip 3 (4-6s): Action. Clip 4 (6-8s): Climax. Clip 5 (8-10s): Reaction/Ending. Overlay: [TEXT]"
    }
    """
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openrouter/free",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "plugins": [{"id": "response-healing"}]
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions", 
        headers=headers, 
        json=payload
    )
    
    response_data = response.json()
    
    if 'choices' not in response_data:
        print("❌ OPENROUTER API ERROR:")
        print(json.dumps(response_data, indent=2))
        raise ValueError("OpenRouter request failed. Check logs.")
        
    raw_text = response_data['choices'][0]['message']['content']
    clean_json = clean_json_response(raw_text)
    
    # --- ERROR HANDLING BLOCK ---
    try:
        data = json.loads(clean_json)
    except json.JSONDecodeError:
        print("❌ FAILED TO PARSE JSON! THIS IS WHAT THE AI RETURNED:")
        print(raw_text)
        raise ValueError("AI returned invalid JSON. See the raw output above.")
    
    # 2. Send Blueprint to Telegram
    msg = f"🚀 *NEW SHORTS PACKAGE: {data['title']}*\n\n"
    msg += f"🎬 *EDIT BLUEPRINT:*\n{data['instructions']}"
    send_telegram_message(msg)

    # 3. Download 5 Clips
    print("2. Scraping & Downloading 5 Vertical Video Clips...")
    download_dir = "downloaded_clips"
    download_vertical_clips(data["search_term"], output_dir=download_dir, max_clips=5)

    # 4. Send MP4s to Telegram
    print("3. Sending MP4 Files to Telegram...")
    video_files = sorted(glob.glob(f"{download_dir}/*.mp4"))
    
    if not video_files:
        send_telegram_message("⚠️ No video clips were retrieved automatically.")
    else:
        for idx, vid_path in enumerate(video_files[:5], start=1):
            send_telegram_video(vid_path, caption=f"📹 Raw Clip #{idx}")

    print("✅ Finished sending instructions and videos!")

if __name__ == "__main__":
    asyncio.run(run_pipeline())

import os
import json
import re
import asyncio
import requests
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not BOT_TOKEN or not CHAT_ID or not OPENROUTER_KEY:
    raise ValueError("Missing Secrets: OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN, or TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def clean_json_response(text):
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    
    match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0).strip()
    return text.strip()

async def run_pipeline():
    print("1. Querying AI via OpenRouter for 5 Daily Ideas...")
    
    # 🚀 NEW: Prompt locked to ONLY Basketball and Volleyball, tailored for the white-background meme format.
    prompt = """
    You are a professional viral sports content producer for TikTok and Instagram Reels.
    Generate 5 viral concept ideas for 9:16 vertical short videos in English only.
    
    CRITICAL INSTRUCTIONS:
    - SPORT RESTRICTION: STRICTLY focus ONLY on Basketball (e.g., NBA, streetball, college) and Volleyball (e.g., VNL, men's/women's indoors, beach, crazy spikes/saves). DO NOT generate ideas for any other sports.
    - VISUAL FORMAT: The video will have the raw sports footage centered with a white background at the top and bottom (meme-style).
    - "overlay_text": Must be a short, highly engaging hook meant to be placed in the top white margin in bold text. Use Gen-Z/TikTok slang or POV formats (e.g., "BRO REALLY THOUGHT HE HAD A CHANCE 💀", "LIBERO WAS FIGHTING FOR HIS LIFE 😭", "POV: YOU TRIGGERED HIS PRIME MODE 🔥"). Keep it punchy.
    - "seo_caption": MUST start with a 1-2 sentence engaging description or question to drive comments, followed by 5-7 SEO hashtags. Do not just output hashtags alone.
    
    Return strictly a JSON object with an "ideas" array containing 5 items:
    {
        "ideas": [
            {
                "content_idea": "Description of the basketball or volleyball highlight concept",
                "title": "Short Catchy Title",
                "search_term": "crazy volleyball libero saves",
                "overlay_text": "LIBERO WAS FIGHTING FOR HIS LIFE 😭",
                "seo_caption": "There is absolutely no way he saved this in the 5th set! Who is the best defensive player in the world right now? 👇 #volleyball #vnl #volleyballsaves #sportsedits"
            }
        ]
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
        raise ValueError("OpenRouter request failed.")
        
    raw_text = response_data['choices'][0]['message']['content']
    clean_json = clean_json_response(raw_text)
    
    try:
        data = json.loads(clean_json)
        if isinstance(data, list):
            ideas = data
        elif isinstance(data, dict):
            ideas = data.get("ideas", [])
        else:
            ideas = []
    except json.JSONDecodeError:
        print("❌ FAILED TO PARSE JSON:")
        print(raw_text)
        raise ValueError("AI returned invalid JSON.")
    
    if not ideas:
        raise ValueError("No ideas array found in AI response.")

    ph_date = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d')

    send_telegram_message("🔥 *DAILY SPORTS SHORTS BATCH (5 IDEAS)* 🔥\n-----------------------------------")

    for idx, idea in enumerate(ideas, start=1):
        raw_search_term = idea.get('search_term', 'sports highlights').replace('"', '')
        search_query = f"{raw_search_term} #shorts"
        video_folder = f"video-{idx}"
        
        output_path = f"{ph_date}/{video_folder}/clip_%(autonumber)s.%(ext)s"
        
        scrape_command = f'yt-dlp "ytsearch30:{search_query}" --match-filter "duration <= 60" -f "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/best[vcodec^=avc1][ext=mp4]/best[ext=mp4]" -i --max-downloads 5 -o "{output_path}"'
        merge_command = f'python merge_clips.py {ph_date} {video_folder}'
        
        msg = f"📌 *IDEA #{idx}: {idea.get('title', 'Highlight')}*\n\n"
        msg += f"💡 *Concept:* {idea.get('content_idea', '')}\n\n"
        msg += f"🔠 *Top Overlay Text:* `{idea.get('overlay_text', '')}`\n\n"
        msg += f"📱 *Caption & Hashtags:*\n{idea.get('seo_caption', '')}\n\n"
        msg += f"💻 *Local Terminal Scrape Script:*\n`{scrape_command}`\n\n"
        msg += f"🎬 *Local Merge Script:*\n`{merge_command}`"
        
        send_telegram_message(msg)

    print("✅ Successfully sent 5 daily content packages!")

if __name__ == "__main__":
    asyncio.run(run_pipeline())

import yt_dlp
import time
import random
from typing import Optional

def resolve_youtube_to_direct_url(url: str, retries: int = 3) -> str:
    """
    Resolves a YouTube URL to a direct stream URL locally.
    Uses mobile/TV clients which often bypass "Sign in" blocks.
    """
    print(f"📡 Resolving YouTube URL locally: {url}")
    
    # Prioritize clients that are less likely to hit the bot challenge
    # TV and IOS are currently the strongest for bypassing.
    client_configs = [
        {"player_client": ["tv", "ios"], "player_skip": ["web"]},
        {"player_client": ["android", "ios"], "player_skip": ["web"]},
        {"player_client": ["mweb", "tv"], "player_skip": ["web"]}
    ]
    
    user_agents = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]

    last_error = ""
    for i in range(retries):
        strat = client_configs[i % len(client_configs)]
        ua = random.choice(user_agents)
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": "best",
            "extractor_args": {"youtube": strat},
            "http_headers": {
                "User-Agent": ua,
            },
            "nocheckcertificate": True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # We also attempt to use the 'embed' URL logic if possible
                target_url = url
                if "watch?v=" in url:
                    video_id = url.split("v=")[1].split("&")[0]
                    target_url = f"https://www.youtube.com/embed/{video_id}"
                
                info = ydl.extract_info(target_url, download=False)
                direct_url = info.get("url")
                if direct_url:
                    print(f"✅ Resolved to: {str(direct_url)[:80]}...")
                    return direct_url
        except Exception as e:
            last_error = str(e)
            print(f"⚠️ Attempt {i+1} failed: {last_error}")
            time.sleep(i + 1)
                
    raise RuntimeError(
        f"YouTube resolution failed. YouTube is blocking your IP.\n"
        f"Try a different video or wait a few minutes."
    )

def is_youtube(url: str) -> bool:
    u = (url or "").lower()
    return ("youtube.com" in u) or ("youtu.be" in u) or ("m.youtube.com" in u)

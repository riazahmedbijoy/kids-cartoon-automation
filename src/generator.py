# FILE: src/generator.py
import os
import json
import time
import requests
import urllib.parse
import asyncio
import edge_tts
from io import BytesIO
from google import genai
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from moviepy.config import change_settings
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ASSETS_PATH = Path("assets")
FONT_FILE = ASSETS_PATH / "fonts/arial.ttf"
FALLBACK_THUMBNAIL_FONT = ImageFont.load_default()
YOUR_NAME = "Kids Story"

if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

GEMINI_MODELS = [
    'gemini-3.8-flash', 'gemini-3.5-flash-lite', 'gemini-2.0-flash', 'gemini-1.5-flash'
]

def get_cartoon_image(prompt):
    """Generates only ONE image to avoid API limits."""
    print(f"🎨 Generating Cover Image for: '{prompt}'...")
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true&seed={int(time.time())}"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"❌ Error generating image: {e}. Using gradient background.")
        img = Image.new('RGBA', (1080, 1920), color=(20, 30, 50))
        return img

def text_to_speech_edge(text, output_path):
    """Uses Microsoft Edge's realistic neural voices."""
    print(f"🎤 Converting script to speech using Edge TTS...")
    async def _generate():
        voice = "en-US-AnaNeural" 
        rate = "-10%"
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(str(output_path))
        
    try:
        asyncio.run(_generate())
        return Path(output_path)
    except Exception as e:
        print(f"❌ ERROR: Failed to generate speech: {e}")
        raise

def generate_curriculum(previous_titles=None):
    print("🤖 Generating a new Kids Story curriculum...")
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    prompt = """
    You are a children's storyteller. Generate a curriculum for a YouTube series called 'Kids Bedtime Stories'.
    Respond with ONLY a valid JSON object. The object must contain a key "lessons" which is a list of 10 lesson objects.
    Each lesson object must have these keys: "chapter", "part", "title", "status" (defaulted to "pending"), and "youtube_id" (defaulted to null).
    Topics should be about magical animals, adventures, and moral stories.
    """
    response = None
    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            break
        except Exception:
            time.sleep(2)
    if not response: raise Exception("All models failed.")
    json_string = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(json_string)

def generate_lesson_content(lesson_title):
    print(f"🤖 Writing story: '{lesson_title}'...")
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    prompt = f"""
    You are a master children's storyteller. Write a highly engaging 2-minute bedtime story about '{lesson_title}'.
    Generate a JSON response with these keys:
    1. "story_text": A 150-200 word story for kids. Use descriptive, expressive English with a clear moral.
    2. "image_prompt": A single detailed prompt for a beautiful 3D Pixar-style cartoon cover image representing this story.
    3. "hashtags": A string of 3-5 relevant hashtags (e.g., "#BedtimeStories #KidsStories").
    Return only valid JSON.
    """
    response = None
    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            break
        except Exception:
            time.sleep(2)
    if not response: raise Exception("Failed to generate content.")
    json_string = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(json_string)

def create_video(image_path, audio_path, output_path):
    print(f"🎬 Creating Audio-Story Video...")
    
    audio_clip = AudioFileClip(str(audio_path))
    duration = audio_clip.duration
    
    # FIX: Converting image_path to string so MoviePy can read it
    clip = ImageClip(str(image_path)).set_duration(duration)
    clip = clip.resize(lambda t: 1 + 0.10 * (t / duration))
    clip = clip.set_audio(audio_clip)
    
    clip.write_videofile(
        str(output_path), fps=24, codec="libx264", audio_codec="aac", audio_bitrate="192k", preset="medium", threads=4
    )
    print(f"✅ Story Video created successfully!")

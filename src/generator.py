# FILE: src/generator.py
import os
import json
import time
import requests
import urllib.parse
from io import BytesIO
from google import genai
from gtts import gTTS
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from moviepy.config import change_settings
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from pydub import AudioSegment

# --- Configuration ---
ASSETS_PATH = Path("assets")
FONT_FILE = ASSETS_PATH / "fonts/arial.ttf"
FALLBACK_THUMBNAIL_FONT = ImageFont.load_default()
YOUR_NAME = "Kids Cartoon"

if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

# অটোমেটিক মডেল ট্রাই করার লিস্ট
GEMINI_MODELS = [
    'gemini-3.8-flash', 'gemini-3.5-flash-lite', 'gemini-2.0-flash', 
    'gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-1.5-pro'
]

def get_cartoon_image(prompt):
    """Uses the free Pollinations AI to generate a 3D cartoon image."""
    print(f"🎨 Generating Cartoon Image for: '{prompt}'...")
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"❌ Error generating image: {e}. Using solid background.")
        return Image.new('RGBA', (1080, 1920), color=(12, 17, 29))

def text_to_speech(text, output_path):
    print(f"🎤 Converting script to speech...")
    temp_mp3_path = str(output_path).replace('.mp3', '_temp.mp3')
    wav_path = str(output_path.with_suffix('.wav'))
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(temp_mp3_path)
        audio = AudioSegment.from_mp3(temp_mp3_path)
        audio.export(wav_path, format="wav", codec="pcm_s16le")
        os.remove(temp_mp3_path)
        return Path(wav_path)
    except Exception as e:
        print(f"❌ ERROR: Failed to generate speech: {e}")
        raise

def generate_curriculum(previous_titles=None):
    print("🤖 Generating a new Kids Story curriculum...")
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    prompt = """
    You are a children's storyteller. Generate a curriculum for a YouTube Shorts series called 'Kids Cartoon Stories'.
    Respond with ONLY a valid JSON object. The object must contain a key "lessons" which is a list of 10 lesson objects.
    Each lesson object must have these keys: "chapter", "part", "title", "status" (defaulted to "pending"), and "youtube_id" (defaulted to null).
    Topics should be about cute animals, magical lands, or learning good habits (e.g., 'The Brave Little Lion', 'Timmy the Talking Tree').
    """
    
    response = None
    for model_name in GEMINI_MODELS:
        try:
            print(f"🔄 Trying model: {model_name} for curriculum...")
            response = client.models.generate_content(model=model_name, contents=prompt)
            break
        except Exception as e:
            print(f"⚠️ Model {model_name} failed. Trying next...")
            time.sleep(2)
            
    if not response: raise Exception("❌ All models failed.")
    json_string = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(json_string)

def generate_lesson_content(lesson_title):
    print(f"🤖 Writing story: '{lesson_title}'...")
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    prompt = f"""
    You are a children's storyteller. Write a very short, engaging story for a YouTube Short about '{lesson_title}'.
    Generate a JSON response with three keys:
    1. "story_text": A 40-50 word story for kids. Use simple English.
    2. "image_prompt": A detailed prompt to generate a 3D Pixar-style cartoon image matching the story. (e.g., "A cute brave little lion in a magical jungle, 3D cartoon style, vibrant colors, highly detailed")
    3. "hashtags": A string of 3-5 relevant hashtags (e.g., "#KidsStories #Cartoon #Shorts").
    Return only valid JSON.
    """
    
    response = None
    for model_name in GEMINI_MODELS:
        try:
            print(f"🔄 Trying model: {model_name} for lesson content...")
            response = client.models.generate_content(model=model_name, contents=prompt)
            break
        except Exception as e:
            print(f"⚠️ Model {model_name} failed. Trying next...")
            time.sleep(2)
            
    if not response: raise Exception(f"❌ Failed to generate content for {lesson_title}.")
    json_string = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(json_string)

def generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0):
    output_dir.mkdir(exist_ok=True, parents=True)
    is_thumbnail = thumbnail_title is not None
    width, height = (1080, 1920) # Only Shorts format
    
    title = thumbnail_title if is_thumbnail else slide_content.get("title", "")
    image_prompt = slide_content.get("image_prompt", title) if not is_thumbnail else title
    
    bg_image = get_cartoon_image(image_prompt)
    bg_image = bg_image.resize((width, height))
    
    draw = ImageDraw.Draw(bg_image)
    try:
        title_font = ImageFont.truetype(str(FONT_FILE), 80)
        content_font = ImageFont.truetype(str(FONT_FILE), 60)
    except IOError:
        title_font = content_font = FALLBACK_THUMBNAIL_FONT

    if not is_thumbnail:
        content = slide_content.get("content", "")
        # Add a semi-transparent box for text readability
        draw.rectangle([50, 1400, 1030, 1800], fill=(0, 0, 0, 150))
        
        words = content.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if draw.textbbox((0, 0), test_line, font=content_font)[2] < width * 0.85:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        y_text = 1450
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=content_font)
            x = (width - (bbox[2] - bbox[0])) / 2
            draw.text((x, y_text), line, font=content_font, fill=(255, 255, 255), stroke_width=2, stroke_fill="black")
            y_text += 80

    file_prefix = "thumbnail" if is_thumbnail else f"slide_{slide_number:02d}"
    path = output_dir / f"{file_prefix}.png"
    bg_image.convert("RGB").save(path)
    return str(path)

def create_video(slide_paths, audio_paths, output_path, video_type):
    print(f"🎬 Creating Short Video...")
    if not slide_paths or not audio_paths or len(slide_paths) != len(audio_paths):
        raise ValueError("Mismatch between slides and audio clips.")

    image_clips = []
    for i, (img_path, audio_path) in enumerate(zip(slide_paths, audio_paths)):
        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration + 0.5
        img_clip = ImageClip(img_path).set_duration(duration).set_audio(audio_clip).fadein(0.5).fadeout(0.5)
        image_clips.append(img_clip)

    final_video = concatenate_videoclips(image_clips, method="compose")
    final_video.write_videofile(
        str(output_path), fps=24, codec="libx264", audio_codec="aac", audio_bitrate="192k", preset="medium", threads=4
    )
    print(f"✅ Short video created successfully!")

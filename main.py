# FILE: main.py
import os
import sys
import json
import datetime
import traceback
from pathlib import Path
from src.generator import (
    generate_curriculum,
    generate_lesson_content,
    text_to_speech_edge, # নতুন ভয়েস ইমপোর্ট
    get_cartoon_image,   # শুধু ১টি ছবির জন্য
    create_video,
    YOUR_NAME
)
from src.uploader import upload_to_youtube

CONTENT_PLAN_FILE = Path("content_plan.json")
OUTPUT_DIR = Path("output")
LESSONS_PER_RUN = 1

def get_content_plan():
    if not CONTENT_PLAN_FILE.exists():
        new_plan = generate_curriculum()
        with open(CONTENT_PLAN_FILE, 'w') as f:
            json.dump(new_plan, f, indent=2)
        return new_plan
    else:
        try:
            with open(CONTENT_PLAN_FILE, 'r') as f:
                plan = json.load(f)
            return plan
        except Exception:
            new_plan = generate_curriculum()
            with open(CONTENT_PLAN_FILE, 'w') as f:
                json.dump(new_plan, f, indent=2)
            return new_plan

def update_content_plan(plan):
    with open(CONTENT_PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)

def produce_story_video(lesson):
    print(f"\n▶️ Starting production for Bedtime Story: '{lesson['title']}'")
    unique_id = f"{datetime.datetime.now().strftime('%Y%m%d')}_{lesson['chapter']}"
    
    # 1. Generate Story and Cover Image Prompt (1টি ছবি)
    lesson_content = generate_lesson_content(lesson['title'])
    story_text = lesson_content['story_text']
    image_prompt = lesson_content['image_prompt']
    hashtags = lesson_content.get("hashtags", "#BedtimeStories #Kids")
    
    print(f"📖 Story: {story_text}")
    
    # 2. Generate Realistic Audio (Edge TTS)
    audio_mp3_path = OUTPUT_DIR / f"audio_{unique_id}.mp3"
    audio_path = text_to_speech_edge(story_text, audio_mp3_path)
    
    # 3. Generate ONE Cover Image
    slide_dir = OUTPUT_DIR / f"slides_{unique_id}"
    slide_dir.mkdir(exist_ok=True, parents=True)
    image_path = slide_dir / "cover.png"
    
    img = get_cartoon_image(image_prompt)
    img.resize((1080, 1920)).convert("RGB").save(image_path)
    
    # 4. Create Video (1টি ছবি + অডিও)
    video_path = OUTPUT_DIR / f"video_{unique_id}.mp4"
    create_video(image_path, audio_path, video_path)
    
    # 5. Upload to YouTube
    print("\n📤 Uploading Video to YouTube...")
    video_desc = f"{story_text}\n\n{hashtags}"
    video_title = f"{lesson['title']} - Bedtime Story" 
    
    video_id = upload_to_youtube(
        video_path,
        video_title,
        video_desc,
        "Kids, Bedtime Stories, Audio Story, Cartoon",
        image_path # থাম্বনেইল হিসেবে কভার ছবি
    )
    
    return video_id

def main():
    print("🚀 Starting Kids Bedtime Story Generator")
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    try:
        plan = get_content_plan()
        pending = [(i, lesson) for i, lesson in enumerate(plan['lessons']) if lesson['status'] == 'pending']

        if not pending:
            new_plan = generate_curriculum()
            update_content_plan(new_plan)
            plan = new_plan
            pending = [(i, lesson) for i, lesson in enumerate(new_plan['lessons']) if lesson['status'] == 'pending']
            if not pending: return

        failed = []
        for lesson_index, lesson in pending[:LESSONS_PER_RUN]:
            try:
                video_id = produce_story_video(lesson)
                if video_id:
                    for original_lesson in plan['lessons']:
                        if original_lesson['title'].strip().lower() == lesson['title'].strip().lower():
                            original_lesson['status'] = 'complete'
                            original_lesson['youtube_id'] = video_id
                            print(f"✅ Completed: {lesson['title']}")
                            break
                else:
                    failed.append(lesson['title'])
            except Exception as e:
                print(f"❌ Failed: {lesson['title']}")
                traceback.print_exc()
                failed.append(lesson['title'])
            finally:
                update_content_plan(plan)

        if failed:
            sys.exit(1)

    except Exception as e:
        print("❌ Critical error in main()")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

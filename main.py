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
    text_to_speech,
    generate_visuals,
    create_video,
    YOUR_NAME
)
from src.uploader import upload_to_youtube

CONTENT_PLAN_FILE = Path("content_plan.json")
OUTPUT_DIR = Path("output")
LESSONS_PER_RUN = 1

def get_content_plan():
    if not CONTENT_PLAN_FILE.exists():
        print("📄 content_plan.json not found. Generating new plan...")
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

def produce_video(lesson):
    print(f"\n▶️ Starting production for Kids Video: '{lesson['title']}'")
    unique_id = f"{datetime.datetime.now().strftime('%Y%m%d')}_{lesson['chapter']}"
    
    # 1. Generate Long Story with 6 Scenes
    lesson_content = generate_lesson_content(lesson['title'])
    story_text = lesson_content['story_text']
    scenes = lesson_content['scenes']
    hashtags = lesson_content.get("hashtags", "#KidsStories #Cartoon")
    
    # 2. Generate Audio for the whole story
    audio_mp3_path = OUTPUT_DIR / f"audio_{unique_id}.mp3"
    audio_path = text_to_speech(story_text, audio_mp3_path)
    
    # 3. Generate Images for each scene
    slide_dir = OUTPUT_DIR / f"slides_{unique_id}"
    slide_paths = []
    for i, scene in enumerate(scenes):
        path = generate_visuals(
            output_dir=slide_dir,
            video_type='video',
            scene_text=scene['text'],
            image_prompt=scene['image_prompt'],
            slide_number=i+1
        )
        slide_paths.append(path)
    
    # 4. Create Animated Video (Pulse & Zoom Effect)
    video_path = OUTPUT_DIR / f"video_{unique_id}.mp4"
    create_video(slide_paths, audio_path, video_path)
    
    # 5. Upload to YouTube
    print("\n📤 Uploading Video to YouTube...")
    video_desc = f"{story_text}\n\n{hashtags}"
    video_title = f"{lesson['title']}" 
    
    video_id = upload_to_youtube(
        video_path,
        video_title,
        video_desc,
        "Kids, Cartoon, Stories, Animation",
        slide_paths[0] 
    )
    
    return video_id

def main():
    print("🚀 Starting Kids Cartoon Video Generator")
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    try:
        plan = get_content_plan()
        pending = [(i, lesson) for i, lesson in enumerate(plan['lessons']) if lesson['status'] == 'pending']

        if not pending:
            print("🎉 All stories produced! Generating new curriculum...")
            new_plan = generate_curriculum()
            update_content_plan(new_plan)
            plan = new_plan
            pending = [(i, lesson) for i, lesson in enumerate(new_plan['lessons']) if lesson['status'] == 'pending']
            if not pending: return

        failed = []
        for lesson_index, lesson in pending[:LESSONS_PER_RUN]:
            try:
                video_id = produce_video(lesson)
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

import os
import json
import requests
from io import BytesIO
import google.generativeai as genai
from gtts import gTTS
from moviepy.editor import AudioFileClip, ImageClip, CompositeAudioClip, concatenate_videoclips, vfx
from moviepy.config import change_settings
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
from pydub import AudioSegment

# --- Configuration ---
ASSETS_PATH = Path("assets")
FONT_FILE = ASSETS_PATH / "fonts/arial.ttf"
BACKGROUND_MUSIC_PATH = ASSETS_PATH / "music/bg_music.mp3"
FALLBACK_THUMBNAIL_FONT = ImageFont.load_default()
YOUR_NAME = "Chaitanya"

if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})


# ==============================
# IMAGE FETCHING
# ==============================

def get_pexels_image(query, video_type):
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key:
        print("⚠️ PEXELS_API_KEY not found. Using solid color background.")
        return None

    orientation = 'landscape' if video_type == 'long' else 'portrait'
    try:
        headers = {"Authorization": pexels_api_key}
        params = {"query": f"abstract {query}", "per_page": 1, "orientation": orientation}
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get('photos'):
            image_url = data['photos'][0]['src']['large2x']
            image_response = requests.get(image_url, timeout=15)
            image_response.raise_for_status()
            return Image.open(BytesIO(image_response.content)).convert("RGBA")

    except Exception as e:
        print(f"❌ Error fetching Pexels image: {e}")

    return None


# ==============================
# TEXT TO SPEECH
# ==============================

def text_to_speech(text, output_path):
    print("🎤 Converting script to speech...")
    try:
        temp_mp3 = str(output_path).replace('.mp3', '_temp.mp3')
        wav_path = str(output_path.with_suffix('.wav'))

        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(temp_mp3)

        audio = AudioSegment.from_mp3(temp_mp3)
        audio.export(wav_path, format="wav", codec="pcm_s16le")
        os.remove(temp_mp3)

        print("✅ Speech generated successfully!")
        return Path(wav_path)

    except Exception as e:
        print(f"❌ ERROR: Failed to generate speech: {e}")
        raise


# ==============================
# GEMINI CONTENT GENERATION
# ==============================

def generate_curriculum():
    print("🤖 Generating curriculum...")
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model = genai.GenerativeModel("models/text-bison-001")

        prompt = f"""
        Generate a structured curriculum for a YouTube series called
        'AI for Developers by {YOUR_NAME}'.

        Return ONLY valid JSON with:
        {{
          "lessons": [
            {{
              "chapter": "",
              "part": "",
              "title": "",
              "status": "pending",
              "youtube_id": null
            }}
          ]
        }}
        """

        response = model.generate_content(prompt)
        curriculum = json.loads(response.text.strip())
        print("✅ Curriculum generated.")
        return curriculum

    except Exception as e:
        print(f"❌ Curriculum generation failed: {e}")
        raise


def generate_lesson_content(lesson_title):
    print(f"🤖 Generating lesson: {lesson_title}")
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model = genai.GenerativeModel("models/text-bison-001")

        prompt = f"""
        Create beginner-friendly AI lesson content for:
        "{lesson_title}"

        Return JSON:
        {{
          "long_form_slides": [
            {{"title": "", "content": ""}}
          ],
          "short_form_highlight": "",
          "hashtags": ""
        }}
        """

        response = model.generate_content(prompt)
        content = json.loads(response.text.strip())
        print("✅ Lesson content generated.")
        return content

    except Exception as e:
        print(f"❌ Lesson generation failed: {e}")
        raise


# ==============================
# SLIDE GENERATION
# ==============================

def generate_visuals(output_dir, video_type, slide_content=None,
                     thumbnail_title=None, slide_number=0, total_slides=0):

    output_dir.mkdir(exist_ok=True, parents=True)
    is_thumbnail = thumbnail_title is not None

    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    title = thumbnail_title if is_thumbnail else slide_content.get("title", "")

    bg_image = get_pexels_image(title, video_type)
    if not bg_image:
        bg_image = Image.new('RGBA', (width, height), color=(12, 17, 29))

    bg_image = bg_image.resize((width, height)).filter(ImageFilter.GaussianBlur(5))
    dark_overlay = Image.new('RGBA', bg_image.size, (0, 0, 0, 150))
    final_bg = Image.alpha_composite(bg_image, dark_overlay).convert("RGB")

    draw = ImageDraw.Draw(final_bg)

    try:
        title_font = ImageFont.truetype(str(FONT_FILE), 70)
        content_font = ImageFont.truetype(str(FONT_FILE), 45)
    except:
        title_font = content_font = FALLBACK_THUMBNAIL_FONT

    if is_thumbnail:
        bbox = draw.textbbox((0, 0), title, font=title_font)
        x = (width - (bbox[2] - bbox[0])) / 2
        y = (height - (bbox[3] - bbox[1])) / 2
        draw.text((x, y), title, font=title_font, fill="white")
    else:
        draw.text((100, 100), title, font=title_font, fill="white")
        draw.text((100, 250), slide_content.get("content", ""),
                  font=content_font, fill=(220, 220, 220))

    filename = "thumbnail.png" if is_thumbnail else f"slide_{slide_number}.png"
    path = output_dir / filename
    final_bg.save(path)
    return str(path)


# ==============================
# VIDEO CREATION
# ==============================

def create_video(slide_paths, audio_paths, output_path, video_type):
    print(f"🎬 Creating {video_type} video...")

    clips = []

    for img, audio in zip(slide_paths, audio_paths):
        audio_clip = AudioFileClip(str(audio))
        img_clip = (
            ImageClip(img)
            .set_duration(audio_clip.duration + 0.5)
            .set_audio(audio_clip)
        )
        clips.append(img_clip)

    final_video = concatenate_videoclips(clips, method="compose")

    final_video.write_videofile(
        str(output_path),
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    print("✅ Video created successfully!")

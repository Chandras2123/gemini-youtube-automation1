# src/generator.py

import os
from google import genai

# Load API key from environment variable
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not found in environment variables")

# Create client
client = genai.Client(api_key=API_KEY)


def generate_lesson_content(title: str) -> str:
    """
    Generate structured lesson content using Gemini.
    """

    print(f"🤖 Generating content for lesson: '{title}'...")

    prompt = f"""
    Create a detailed, structured lesson script for a YouTube course.

    Lesson Title: {title}

    Structure:
    1. Hook (engaging intro)
    2. Concept Explanation
    3. Real-world example
    4. Practical use case
    5. Summary
    6. Call to action

    Make it clear, beginner-friendly, and professional.
    """

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash-latest",
            contents=prompt
        )

        print("✅ Content generated successfully.")
        return response.text

    except Exception as e:
        print(f"❌ ERROR generating lesson content: {e}")
        raise

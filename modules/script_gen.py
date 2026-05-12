import google.generativeai as genai
import os
import json

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

def generate_script(topic: str, duration: int) -> dict:
    """
    Generate a script, scene breakdown, search terms for stock footage,
    and captions with timing for the given topic and target duration.
    """
    word_count = duration * 2  # rough estimate: 2 words per second

    prompt = f"""
    You are a viral content scriptwriter. Write a voiceover script about:
    "{topic}"

    The script must be around {word_count} words, suitable for a {duration}-second video.
    
    Return your response as a valid JSON object with these keys:
    - "full_text": the complete voiceover script text
    - "scenes": a list of objects, each with:
        - "text": the scene's spoken text
        - "duration": estimated duration in seconds for this scene
        - "search_term": a Pexels search term for stock footage to match this scene
    - "captions": a list of objects, each with:
        - "text": the caption phrase (exactly as it should appear on screen)
        - "start_time": the start time in seconds
        - "end_time": the end time in seconds
    
    Caption timing must sync with the voiceover. Use dynamic, eye-catching phrases.
    """

    response = model.generate_content(prompt)
    
    # Parse the JSON response
    try:
        # Clean the response text - remove markdown code fences if present
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        data = json.loads(text)
        return data
    except json.JSONDecodeError:
        # Fallback: create basic structure
        fallback = {
            "full_text": response.text,
            "scenes": [
                {"text": response.text, "duration": duration, "search_term": topic}
            ],
            "captions": [
                {"text": response.text[:30], "start_time": 0, "end_time": duration}
            ]
        }
        return fallback

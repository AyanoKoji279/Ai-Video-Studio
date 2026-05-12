import requests
import os

OUTPUT_DIR = "outputs/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_ai_image(scenes: list) -> list:
    """
    Generate AI images for scenes using Pollinations.ai (free, no API key).
    Returns a list of local image paths.
    """
    image_paths = []
    for i, scene in enumerate(scenes):
        prompt = scene.get("text", "abstract background")
        # Pollinations free endpoint
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1080&height=1920&nologo=true"
        
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                filename = f"scene_{i+1}.jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                image_paths.append(filepath)
            else:
                # If fail, still append something (the video assembly will handle None/missing)
                image_paths.append(None)
        except Exception:
            image_paths.append(None)
    return image_paths

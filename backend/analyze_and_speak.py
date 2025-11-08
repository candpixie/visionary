#!/usr/bin/env python3
"""
Analyze Image and Speak
Analyzes an image with Claude API and plays the scene description via ElevenLabs TTS
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from aiohttp import ClientSession

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass

# Import image analyzer
try:
    from backend.image_analyzer import ImageAnalyzer
    IMAGE_ANALYZER_AVAILABLE = True
except ImportError as e:
    IMAGE_ANALYZER_AVAILABLE = False
    print(f"Error: ImageAnalyzer not available: {e}")
    print("Make sure you're running from project root: python backend/analyze_and_speak.py <image_path>")
    sys.exit(1)


async def generate_tts(text: str, voice: str = "alloy", api_key: str = None, cache_dir: Path = None):
    """
    Generate TTS via ElevenLabs and return audio data
    
    Args:
        text: Text to convert to speech
        voice: ElevenLabs voice ID (default: "alloy")
        api_key: ElevenLabs API key (if None, uses ELEVENLABS_API_KEY env var)
        cache_dir: Directory to cache audio files (optional)
    
    Returns:
        Audio data as bytes, or None on failure
    """
    api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY not set")
        return None
    
    api_base = os.getenv("ELEVENLABS_API_BASE", "https://api.elevenlabs.io/v1")
    tts_url = f"{api_base}/text-to-speech/{voice}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    payload = {"text": text}
    
    try:
        async with ClientSession() as session:
            async with session.post(tts_url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    print(f"ElevenLabs TTS error: {resp.status} {txt}")
                    return None
                audio_data = await resp.read()
                return audio_data
    except Exception as e:
        print(f"Exception calling ElevenLabs: {e}")
        return None


def save_audio(audio_data: bytes, output_path: Path = None):
    """
    Save audio file to disk
    
    Args:
        audio_data: Audio data as bytes (MP3 format)
        output_path: Path to save audio file (if None, saves to tts_cache directory)
    
    Returns:
        Path to saved audio file
    """
    import time
    
    # Determine output path
    if output_path is None:
        tts_cache_dir = project_root / "backend" / "tts_cache"
        tts_cache_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time() * 1000)
        output_path = tts_cache_dir / f"tts_{timestamp}.mp3"
    
    # Save audio file
    try:
        output_path.write_bytes(audio_data)
        print(f"Audio saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving audio file: {e}")
        return None


async def analyze_and_speak(image_path: str):
    """
    Analyze image and speak the scene description
    
    Args:
        image_path: Path to the image file
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        return
    
    try:
        # Initialize image analyzer
        analyzer = ImageAnalyzer()
        
        print(f"Analyzing image: {image_path}")
        analysis = analyzer.analyze_image(image_path)
        
        # Get scene description
        scene_description = analysis.get("scene_description", "Image analyzed")
        print(f"\nScene Description: {scene_description}\n")
        
        # Generate TTS
        print("Generating voice...")
        audio_data = await generate_tts(scene_description)
        
        if audio_data:
            # Save audio file
            saved_path = save_audio(audio_data)
            if saved_path:
                print(f"Done! Audio file saved to: {saved_path}")
            else:
                print("Error: Failed to save audio file")
        else:
            print("Error: Failed to generate TTS audio")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python backend/analyze_and_speak.py <image_path>")
        print("Example: python backend/analyze_and_speak.py tmp/photo_123.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    asyncio.run(analyze_and_speak(image_path))


if __name__ == "__main__":
    main()


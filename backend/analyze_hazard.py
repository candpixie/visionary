#!/usr/bin/env python3
"""
Analyze image for hazards using Anthropic Claude API
Returns structured output with scene description and hazard detection
"""

import sys
import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)

# Load environment variables
load_dotenv()


class HazardAnalyzer:
    """Analyze images for hazards using Claude API"""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables or .env file")

        self.elevenlabs = ElevenLabs(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        )
        
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-20241022"  # Fast model for low latency

    
    def encode_image(self, image_path: str) -> str:
        """Encode image file to base64"""
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    def analyze_image(self, image_data: str) -> Dict[str, Any]:
        """
        Analyze image for hazards and return structured output
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with:
            - scene_description: str
            - object_too_close_on_left_side: "yes" or "no"
            - object_too_close_on_right_side: "yes" or "no"
        """
        
        # Determine image format from file extension
        media_type = "image/jpeg"  # Default
        
        # Create prompt with JSON schema
        prompt = """Analyze this image and provide a structured response in JSON format.

Look for:
1. A clear description of the scene
2. Any objects that are too close on the left side of the frame
3. Any objects that are too close on the right side of the frame

Return ONLY a valid JSON object with this exact structure:
{
  "scene_description": "A short sentence (max 10 words) description of what you see in the image",
  "object_too_close_on_left_side": "yes" or "no",
  "object_too_close_on_right_side": "yes" or "no"
}

Consider an object "too close" if it appears within approximately 2-3 feet (60-90 cm) from the camera's perspective and could pose a collision risk."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # Extract response text
            response_text = message.content[0].text.strip()
            
            # Parse JSON from response (handle cases where Claude adds extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                
                # Validate structure
                required_keys = [
                    "scene_description",
                    "object_too_close_on_left_side",
                    "object_too_close_on_right_side"
                ]
                
                for key in required_keys:
                    if key not in result:
                        raise ValueError(f"Missing required key: {key}")
                
                # Normalize yes/no values
                for key in ["object_too_close_on_left_side", "object_too_close_on_right_side"]:
                    value = str(result[key]).lower().strip()
                    if value in ["yes", "y", "true", "1"]:
                        result[key] = "yes"
                    elif value in ["no", "n", "false", "0"]:
                        result[key] = "no"
                    else:
                        # Default to "no" if unclear
                        result[key] = "no"
                
                return result
            else:
                raise ValueError("No JSON object found in response")
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Response text: {response_text}")
            raise
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            raise


    def save_scene_description(self, scene_description: str) -> Path:
        """
        Save scene description to a .txt file
        
        Args:
            scene_description: The scene description text to save
            image_path: Path to the original image file
            
        Returns:
            Path to the saved .txt file
        """
        # Create .txt filename based on image filename
        txt_path = "description.txt"
        
        # Write scene description to file
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(scene_description)
        
        return txt_path

    def generate_audio(self, scene_description: str) -> None:
        audio = self.elevenlabs.text_to_speech.convert(
            text=scene_description,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        play(audio)


def analyze(image_base64: str, encoded: bool):
    """Main entry point"""
    
    try:
        analyzer = HazardAnalyzer()
        if not encoded:
            image_base64 = analyzer.encode_image(image_base64)
        result = analyzer.analyze_image(image_base64)
        # Print result as JSON
        print(json.dumps(result, indent=2))
        
        # Save scene description to .txt file
        scene_description = result.get("scene_description", "")
        if scene_description:
            txt_path = analyzer.save_scene_description(scene_description)
            analyzer.generate_audio(scene_description)
            print(f"Scene description saved to: {txt_path}", file=sys.stderr)
           
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_hazard.py <image_path>")
        print("\nExample:")
        print("  python analyze_hazard.py /path/to/image.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    analyze(image_path, encoded=False)

if __name__ == "__main__":
    main()


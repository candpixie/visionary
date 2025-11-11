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
import pyaudio
import wave
import io
import time

try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)

# Load environment variables
load_dotenv()
playing_audio = False


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
                        # buzz here L 
                    elif value in ["no", "n", "false", "0"]:
                        result[key] = "no"
                        # buzz here too R
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
    def listen_for_audio(self) -> str:

        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        CHUNK = 1024
        RECORD_SECONDS = 3

        audio = pyaudio.PyAudio()

        # Start Recording
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
        print("Recording for 3 seconds...")
        frames = []

        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        print("Recording finished.")

        # Stop Recording
        stream.stop_stream()
        stream.close()
        audio.terminate()

        # Write the recorded data to a BytesIO buffer as a WAV file
        audio_bytesio = io.BytesIO()
        with wave.open(audio_bytesio, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))

        # Crucial step: seek to the beginning of the BytesIO buffer after writing
        audio_bytesio.seek(0)

        # You can now use 'audio_bytesio' as an in-memory file object
        # For example, pass it to an API or another library that accepts file-like objects or bytes
        # print(f"BytesIO object created, size: {len(audio_bytesio.getvalue())} bytes")



        transcription = self.elevenlabs.speech_to_text.convert(
            file=audio_bytesio,
            model_id="scribe_v1", # Model to use, for now only "scribe_v1" is supported
            tag_audio_events=True, # Tag audio events like laughter, applause, etc.
            language_code="eng", # Language of the audio file. If set to None, the model will detect the language automatically.
            diarize=True, # Whether to annotate who is speaking
        )
        print(type(transcription))
        return transcription

    def generate_audio(self, scene_description: str) -> None:
        global playing_audio
        if playing_audio:
            return
            
        playing_audio = True

        audio = self.elevenlabs.text_to_speech.convert(
            text=scene_description,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        play(audio)
        playing_audio = False


def analyze(image_base64: str, encoded: bool, left_arduino, right_arduino, test=False):
    """Main entry point"""
    if test:
        try:
            if left_arduino and left_arduino.is_open:
                        left_arduino.write(b"b")
                        print("[LEFT] Buzz triggered")
            else:
                        print("[LEFT] Arduino not connected")

            if right_arduino and right_arduino.is_open:
                        right_arduino.write(b"b")
                        print("[RIGHT] Buzz triggered")
            else:
                print("[RIGHT] Arduino not connected")
        except Exception as e:
                print(f"Buzzing failed: {e}")  
    else:
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
                print(f"Scene description saved to: {txt_path}", file=sys.stderr)
                
                # buzz if object too close
                try:
                    print(result.get("object_too_close_on_left_side"))
                    print(result.get("object_too_close_on_right_side"))
                    if result.get("object_too_close_on_left_side") == "yes":
                        if left_arduino and left_arduino.is_open:
                            left_arduino.write(b"b")
                            print("[LEFT] Buzz triggered")
                        else:
                            print("[LEFT] Arduino not connected")

                    if result.get("object_too_close_on_right_side") == "yes":
                        if right_arduino and right_arduino.is_open:
                            right_arduino.write(b"b")
                            print("[RIGHT] Buzz triggered")
                        else:
                            print("[RIGHT] Arduino not connected")
                except Exception as e:
                    print(f"Buzzing failed: {e}")
                
                analyzer.generate_audio(scene_description)
            
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

def get_latest_file(directory):
        """Return the path of the latest file in the given directory, or None if empty."""
        files = [os.path.join(directory, f) for f in os.listdir(directory)]
        files = [f for f in files if os.path.isfile(f)]
        if not files:
            return None
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    
def ask_question_about_image(encoded=False) -> str:
    global playing_audio
    playing_audio = True
    print("Asking question about latest image...")
    analyzer = HazardAnalyzer()
    
    file = get_latest_file("tmp")

    if not encoded:
        image_base64 = analyzer.encode_image(file)
    
    # Step 1: Listen for audio and get transcription (the question)
    print("Listening for your question...")
    transcription_result = analyzer.listen_for_audio()
    question = transcription_result.text
    print(f"Question: {question}")
    
    try:
        # Step 2: Use Anthropic vision API to answer the question about the image
        message = analyzer.client.messages.create(
            model=analyzer.model,
            max_tokens=100,  # Limit tokens for short response
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": f"{question}\n\nPlease provide a short, concise answer in exactly one sentence."
                        }
                    ]
                }
            ]
        )
        
        # Extract response text
        response_text = message.content[0].text.strip()
        
        # Ensure it's a single sentence (take first sentence if multiple)
        sentences = response_text.split('.')
        if len(sentences) > 1:
            response_text = sentences[0].strip() + '.'

        print(f"Claude response: {response_text}")
        playing_audio = False

        
        # Step 3: Generate and play audio response
        analyzer.generate_audio(response_text)
        return response_text
        
    except Exception as e:
        error_msg = f"Error generating response: {e}"
        print(error_msg, file=sys.stderr)
        return error_msg

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


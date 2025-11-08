#!/usr/bin/env python3
"""
Claude Image Analyzer
Analyzes images using Anthropic Claude Vision API with structured JSON output
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic library not installed. Install with: pip install anthropic")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Load environment variables from .env file if it exists
if DOTENV_AVAILABLE:
    # Try to load from project root
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Also try current directory
        load_dotenv()


class ImageAnalyzer:
    """Analyzes images using Anthropic Claude Vision API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the image analyzer
        
        Args:
            api_key: Anthropic API key. If None, will try to get from ANTHROPIC_API_KEY env var
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic library is not installed. Install with: pip install anthropic")
        
        if not self.api_key:
            raise ValueError("Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter.")
        
        try:
            self.client = Anthropic(api_key=self.api_key)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Anthropic client: {e}")
    
    def encode_image(self, image_path: Path, max_size: int = 512, quality: int = 75) -> str:
        """
        Encode image file to base64 with compression for faster API calls
        
        Args:
            image_path: Path to the image file
            max_size: Maximum width/height in pixels (default 512 for speed)
            quality: JPEG quality 1-100 (default 75 for balance)
            
        Returns:
            Base64 encoded image string
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # If PIL is available, compress/resize image for faster processing
        if PIL_AVAILABLE:
            try:
                img = Image.open(image_path)
                # Convert to RGB if needed (removes alpha channel)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if image is larger than max_size
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Compress to JPEG in memory
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                buffer.seek(0)
                return base64.b64encode(buffer.read()).decode('utf-8')
            except Exception as e:
                # Fallback to original if compression fails
                print(f"Warning: Image compression failed, using original: {e}")
        
        # Fallback: encode original image
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_image(self, image_path: Path, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze an image using Claude Vision API with structured JSON output
        
        Args:
            image_path: Path to the image file to analyze
            prompt: Custom prompt. If None, uses default prompt
            
        Returns:
            Dictionary with structured analysis results
        """
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")
        
        # Default prompt for visual assistance system (optimized for speed - shorter)
        default_prompt = """Analyze this image for obstacle detection. Provide:
- Scene description
- Main objects
- Environment (indoor/outdoor)
- Potential obstacles
- Movement detected (true/false)
- Safety: safe/caution/warning/danger"""
        
        analysis_prompt = prompt or default_prompt
        
        # Encode image
        try:
            base64_image = self.encode_image(image_path)
        except Exception as e:
            raise RuntimeError(f"Failed to encode image: {e}")
        
        # Define JSON schema for structured output
        json_schema = {
            "type": "object",
            "properties": {
                "scene_description": {
                    "type": "string",
                    "description": "A brief description of what is in the image"
                },
                "main_objects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of main objects detected in the image"
                },
                "environment": {
                    "type": "string",
                    "description": "Description of the environment (indoor/outdoor, location type, etc.)"
                },
                "potential_obstacles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of potential obstacles or hazards detected"
                },
                "movement_detected": {
                    "type": "boolean",
                    "description": "Whether movement or motion is detected in the image"
                },
                "safety_assessment": {
                    "type": "string",
                    "enum": ["safe", "caution", "warning", "danger"],
                    "description": "Overall safety assessment based on the image"
                }
            },
            "required": ["scene_description", "main_objects", "environment", "potential_obstacles", "movement_detected", "safety_assessment"],
            "additionalProperties": False
        }
        
        # Create concise prompt with JSON schema (optimized for speed)
        full_prompt = f"""{analysis_prompt}

Return JSON: {{"scene_description": "...", "main_objects": [...], "environment": "...", "potential_obstacles": [...], "movement_detected": true/false, "safety_assessment": "safe/caution/warning/danger"}}"""
        
        try:
            # Make API call to Claude - using Haiku for maximum speed
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",  # Haiku is 3-5x faster than Sonnet
                max_tokens=300,  # Reduced from 1000 for faster response
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": full_prompt
                            }
                        ]
                    }
                ]
            )
            
            # Parse response (Claude returns content as a list)
            if response.content and len(response.content) > 0:
                content = response.content[0].text
                try:
                    # Try to parse JSON directly
                    analysis = json.loads(content)
                    return analysis
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON from the response
                    # Look for JSON object boundaries
                    try:
                        # Find first { and last }
                        start_idx = content.find('{')
                        end_idx = content.rfind('}')
                        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                            json_str = content[start_idx:end_idx + 1]
                            analysis = json.loads(json_str)
                            return analysis
                        else:
                            raise RuntimeError(f"Could not find JSON in response: {content[:200]}...")
                    except json.JSONDecodeError as e:
                        raise RuntimeError(f"Failed to parse JSON response: {e}\nResponse: {content[:500]}...")
            else:
                raise RuntimeError("Empty response from Claude API")
                
        except Exception as e:
            raise RuntimeError(f"Claude API call failed: {e}")
    
    def analyze_and_save(self, image_path: Path, output_path: Optional[Path] = None, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze image and save results to JSON file
        
        Args:
            image_path: Path to the image file to analyze
            output_path: Path to save JSON results. If None, saves next to image with .json extension
            prompt: Custom prompt. If None, uses default prompt
            
        Returns:
            Dictionary with structured analysis results
        """
        # Analyze image
        analysis = self.analyze_image(image_path, prompt)
        
        # Determine output path
        if output_path is None:
            output_path = image_path.with_suffix('.json')
        
        # Save results
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        return analysis


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python image_analyzer.py <image_path> [output_json_path]")
        print("Example: python image_analyzer.py tmp/photo_123.jpg tmp/analysis_123.json")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    try:
        analyzer = ImageAnalyzer()
        print(f"Analyzing image: {image_path}")
        result = analyzer.analyze_and_save(image_path, output_path)
        
        print("\nAnalysis Results:")
        print(json.dumps(result, indent=2))
        
        if output_path:
            print(f"\nResults saved to: {output_path}")
        else:
            print(f"\nResults saved to: {image_path.with_suffix('.json')}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Simple Claude Chat Completions Script
Makes a simple chat API call to Anthropic Claude
"""

import os
import sys
from pathlib import Path

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Error: anthropic library not installed. Install with: pip install anthropic")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass  # dotenv is optional, will use environment variables directly


def simple_chat(message: str = "hello how are you"):
    """
    Make a simple chat completions call to Claude
    
    Args:
        message: The message to send to the chat model
        
    Returns:
        The response text from the model
    """
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        raise ValueError(
            "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
            "or add it to .env file in the project root."
        )
    
    # Initialize client
    client = Anthropic(api_key=api_key)
    
    try:
        # Make chat completions call
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",  # or "claude-3-5-haiku-20241022" for faster/cheaper
            max_tokens=150,
            messages=[
                {"role": "user", "content": message}
            ]
        )
        
        # Extract and return the response
        if response.content and len(response.content) > 0:
            # Claude returns content as a list of text blocks
            return response.content[0].text
        else:
            return "No response received"
            
    except Exception as e:
        raise RuntimeError(f"Claude API call failed: {e}")


def main():
    """Main function"""
    # Get message from command line or use default
    message = sys.argv[1] if len(sys.argv) > 1 else "hello how are you"
    
    try:
        print(f"Sending: {message}")
        print("\nResponse:")
        response = simple_chat(message)
        print(response)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Navigation system using Claude agent with Google Maps integration
Listens for spoken destination and provides real-time navigation
"""

import time
import requests
import os
import json
from typing import Tuple, Optional, List, Dict, Any
from analyze_hazard import HazardAnalyzer
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
UPDATE_INTERVAL = 5  # seconds between spoken instructions

# Initialize services
analyzer = HazardAnalyzer()
claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)

def speak(text: str):
    """Speak text aloud using ElevenLabs and print to console."""
    print("🎧", text)
    analyzer.generate_audio(text)

def get_current_location() -> Tuple[float, float]:
    """
    Get current GPS coordinates.
    For production, integrate with device GPS or location services.
    For testing, returns a fixed location.
    """
    # TODO: Replace with actual GPS coordinates from device
    # For now, using a default location (can be updated via API or device GPS)
    return (40.3506, -74.6519)  # Default: Princeton University area

def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """Convert address string to coordinates using Google Maps Geocoding API"""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY
    }
    try:
        resp = requests.get(url, params=params, timeout=5).json()
        if resp.get("status") == "OK" and resp.get("results"):
            location = resp["results"][0]["geometry"]["location"]
            return (location["lat"], location["lng"])
        else:
            print(f"Geocoding error: {resp.get('status')}")
            return None
    except Exception as e:
        print(f"Error geocoding address: {e}")
        return None

def get_directions(origin: Tuple[float, float], destination: str) -> Optional[List[str]]:
    """
    Get walking directions from origin coordinates to destination address.
    Returns list of step instructions.
    """
    # First, geocode the destination
    dest_coords = geocode_address(destination)
    if not dest_coords:
        return None
    
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{dest_coords[0]},{dest_coords[1]}",
        "mode": "walking",
        "key": GOOGLE_MAPS_API_KEY
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        if resp.get("status") != "OK":
            print(f"Directions API error: {resp.get('status')}")
            return None
        
        steps = resp["routes"][0]["legs"][0]["steps"]
        instructions = []
        for step in steps:
            instr = step["html_instructions"]
            # Remove basic HTML tags
            instr = instr.replace("<b>", "").replace("</b>", "")
            instr = instr.replace("<div style=\"font-size:0.9em\">", " ").replace("</div>", "")
            instr = instr.replace("<wbr/>", "")
            instructions.append(instr.strip())
        return instructions
    except Exception as e:
        print(f"Error getting directions: {e}")
        return None

def get_distance_and_duration(origin: Tuple[float, float], destination: str) -> Optional[Dict[str, Any]]:
    """Get distance and estimated duration to destination"""
    dest_coords = geocode_address(destination)
    if not dest_coords:
        return None
    
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{dest_coords[0]},{dest_coords[1]}",
        "mode": "walking",
        "key": GOOGLE_MAPS_API_KEY
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        if resp.get("status") == "OK":
            leg = resp["routes"][0]["legs"][0]
            return {
                "distance": leg["distance"]["text"],
                "duration": leg["duration"]["text"]
            }
        return None
    except Exception as e:
        print(f"Error getting distance/duration: {e}")
        return None

def listen_for_destination() -> Optional[str]:
    """Listen for spoken destination using speech-to-text"""
    print("🎤 Listening for destination...")
    speak("Where would you like to go?")
    
    try:
        transcription_result = analyzer.listen_for_audio()
        destination = transcription_result.text.strip()
        print(f"📍 Heard destination: {destination}")
        return destination
    except Exception as e:
        print(f"Error listening for destination: {e}")
        return None

def process_destination_with_claude(user_input: str) -> Optional[str]:
    """
    Use Claude agent to process and normalize the spoken destination.
    Claude will extract and format the destination address using Google Maps tools.
    """
    tools = [
        {
            "name": "geocode_address",
            "description": "Convert an address or place name to coordinates and get formatted address using Google Maps Geocoding API",
            "input_schema": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "The address or place name to geocode (e.g., 'Friend Center, Princeton University' or '123 Main St, New York, NY')"
                    }
                },
                "required": ["address"]
            }
        }
    ]
    
    try:
        # First message to Claude
        messages = [
            {
                "role": "user",
                "content": f"""The user said: "{user_input}"

Please extract the destination address or place name from what the user said. 
If the user said something like "take me to X" or "navigate to Y", extract X or Y.
Use the geocode_address tool to verify and format the destination address properly.

Examples:
- "take me to Friend Center" -> use tool with "Friend Center, Princeton University"
- "navigate to the library" -> use tool with "Princeton University Library, Princeton, NJ"
- "go to 123 Main Street" -> use tool with "123 Main Street"

After using the tool, provide the formatted address that Google Maps returned."""
            }
        ]
        
        # Get Claude's response (may include tool use)
        message = claude_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=500,
            tools=tools,
            messages=messages
        )
        
        # Check if Claude used a tool
        destination = None
        tool_results = []
        
        for content_block in message.content:
            if content_block.type == "tool_use":
                # Claude wants to use the geocode tool
                tool_name = content_block.name
                tool_input = content_block.input
                address_to_geocode = tool_input.get("address", user_input)
                
                # Execute the tool (geocode the address)
                coords = geocode_address(address_to_geocode)
                if coords:
                    # Get formatted address from geocoding result
                    url = "https://maps.googleapis.com/maps/api/geocode/json"
                    params = {
                        "latlng": f"{coords[0]},{coords[1]}",
                        "key": GOOGLE_MAPS_API_KEY
                    }
                    resp = requests.get(url, params=params, timeout=5).json()
                    if resp.get("status") == "OK" and resp.get("results"):
                        formatted_address = resp["results"][0]["formatted_address"]
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Geocoded successfully. Formatted address: {formatted_address}"
                        })
                        destination = formatted_address
                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": f"Could not geocode address: {address_to_geocode}"
                    })
            elif content_block.type == "text":
                # Claude provided text response
                if not destination:
                    destination = content_block.text.strip()
        
        # If Claude used tools, send the results back for final response
        if tool_results:
            # Add assistant message with tool use
            messages.append({
                "role": "assistant",
                "content": message.content
            })
            # Add tool results
            messages.append({
                "role": "user",
                "content": tool_results
            })
            
            final_message = claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=200,
                tools=tools,
                messages=messages
            )
            
            # Extract final destination from Claude's response
            for content_block in final_message.content:
                if content_block.type == "text":
                    # Extract address from Claude's response
                    text = content_block.text
                    # Try to find quoted address or use the formatted address
                    if destination:
                        pass  # Already have destination from tool result
                    else:
                        destination = text.strip()
        
        if destination:
            destination = destination.replace('"', '').strip()
            print(f"🤖 Claude processed destination: {destination}")
            return destination
        else:
            # Fallback to original input
            print(f"⚠️  Using original input as destination: {user_input}")
            return user_input
            
    except Exception as e:
        print(f"Error processing destination with Claude: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to original input
        return user_input

def navigate_to_destination(destination: str):
    """Main navigation loop - continuously updates directions based on current location"""
    print(f"\n🗺️  Starting navigation to: {destination}")
    speak(f"Starting navigation to {destination}")
    
    last_location = None
    step_index = 0
    directions = None
    
    while True:
        # Get current location
        current_location = get_current_location()
        
        # Check if location has changed significantly (more than ~10 meters)
        if last_location:
            # Simple distance check (rough approximation)
            lat_diff = abs(current_location[0] - last_location[0])
            lon_diff = abs(current_location[1] - last_location[1])
            location_changed = (lat_diff > 0.0001 or lon_diff > 0.0001)  # ~10 meters
        else:
            location_changed = True
        
        # Get fresh directions if location changed or first time
        if location_changed or directions is None:
            print(f"\n📍 Current location: {current_location[0]:.6f}, {current_location[1]:.6f}")
            directions = get_directions(current_location, destination)
            
            if not directions:
                speak("Sorry, I can't get directions right now. Please check your connection.")
                break
            
            # Get distance and duration info
            dist_info = get_distance_and_duration(current_location, destination)
            if dist_info:
                info_msg = f"Distance: {dist_info['distance']}, Estimated time: {dist_info['duration']}"
                print(f"📊 {info_msg}")
                speak(info_msg)
            
            step_index = 0
            last_location = current_location
        
        # Check if we've completed all steps
        if step_index >= len(directions):
            # Check if we're close to destination
            dist_info = get_distance_and_duration(current_location, destination)
            if dist_info:
                # If distance is very small, we've arrived
                distance_text = dist_info['distance']
                if 'ft' in distance_text.lower() or 'm' in distance_text.lower():
                    # Extract number
                    try:
                        dist_num = float(''.join(filter(str.isdigit, distance_text.split()[0])))
                        if dist_num < 50:  # Less than 50 feet/meters
                            speak("You have arrived at your destination!")
                            break
                    except:
                        pass
            
            # Recalculate directions from current position
            directions = get_directions(current_location, destination)
            if directions:
                step_index = 0
            else:
                speak("Unable to recalculate directions.")
                break
        
        # Speak the current step
        if directions and step_index < len(directions):
            current_step = directions[step_index]
            print(f"🧭 Step {step_index + 1}/{len(directions)}: {current_step}")
            speak(current_step)
            step_index += 1
        
        # Wait before next update
        time.sleep(UPDATE_INTERVAL)
        
        # Update last location
        last_location = current_location

def main():
    """Main entry point"""
    print("=" * 60)
    print("🗺️  GlaucoGuard Navigation System")
    print("=" * 60)
    
    while True:
        # Listen for destination
        raw_destination = listen_for_destination()
        
        if not raw_destination:
            speak("I didn't catch that. Please try again.")
            time.sleep(2)
            continue
        
        # Process destination with Claude
        destination = process_destination_with_claude(raw_destination)
        
        if not destination:
            speak("I couldn't understand the destination. Please try again.")
            time.sleep(2)
            continue
        
        # Confirm destination
        speak(f"Navigating to {destination}")
        time.sleep(1)
        
        # Start navigation
        navigate_to_destination(destination)
        
        # Ask if user wants to navigate somewhere else
        speak("Navigation complete. Would you like to go somewhere else?")
        time.sleep(3)
        
        # Listen for response
        response = listen_for_destination()
        if response and ("no" in response.lower() or "stop" in response.lower() or "done" in response.lower()):
            speak("Navigation session ended. Goodbye!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Navigation session ended by user.")
        speak("Navigation session ended. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

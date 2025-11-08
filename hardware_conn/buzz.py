import os
import time
import serial
import threading
from dotenv import load_dotenv

load_dotenv()

port = os.getenv("ARDUINO_PORT", "/dev/cu.usbmodemB0818497DA102")
baud = int(os.getenv("BAUD_RATE", "9600"))

arduino = serial.Serial(port, baud, timeout=0.1)
time.sleep(2)
print(f"Connected to {port} at {baud} baud.")
print("Press Enter to buzz, or type 'exit' to quit.\n")

def read_stream():
    while True:
        try:
            line = arduino.readline().decode(errors="ignore").strip()
            if line:
                print(f"[Arduino →] touch={line}")
        except Exception as e:
            print(f"[Error reading stream] {e}")
            break

threading.Thread(target=read_stream, daemon=True).start()

while True:
    try:
        user_input = input("> ").strip().lower()
        if user_input == "exit":
            break
        elif user_input == "":
            arduino.write(b"b")
            print("Buzz sent!")
    except KeyboardInterrupt:
        break

arduino.close()
print("Closed connection.")

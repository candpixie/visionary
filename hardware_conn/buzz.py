import os
import time
import serial
import threading
from dotenv import load_dotenv

load_dotenv()

left_port = os.getenv("LEFT_ARDUINO_PORT", "/dev/cu.usbmodemB0818497DA102")
right_port = os.getenv("RIGHT_ARDUINO_PORT", "/dev/cu.usbmodemB0818499D0202")
baud = int(os.getenv("BAUD_RATE", "9600"))

time.sleep(2)

def connect_arduino(port, label):
    """Try to connect to a given port and return Serial object or None."""
    try:
        arduino = serial.Serial(port, baud, timeout=0.1)
        time.sleep(2)
        print(f"[{label}] Connected.")
        return arduino
    except Exception as e:
        print(f"[{label}] Connection failed: {e}")
        return None


left_arduino = connect_arduino(left_port, "LEFT")
right_arduino = connect_arduino(right_port, "RIGHT")

def read_stream(arduino, label):
    """Continuously read lines and print only touch readings."""
    while arduino and arduino.is_open:
        try:
            line = arduino.readline().decode(errors="ignore").strip()
            if line and "touch" in line.lower():
                print(f"[{label}] {line}")
        except Exception as e:
            print(f"[{label}] Error: {e}")
            break


if left_arduino:
    threading.Thread(target=read_stream, args=(left_arduino, "LEFT"), daemon=True).start()
if right_arduino:
    threading.Thread(target=read_stream, args=(right_arduino, "RIGHT"), daemon=True).start()


while True:
    try:
        user_input = input().strip().lower()
        if user_input == "exit":
            break
        elif user_input == "l" and left_arduino:
            left_arduino.write(b"b")
        elif user_input == "r" and right_arduino:
            right_arduino.write(b"b")
    except KeyboardInterrupt:
        break

# Close everything
if left_arduino:
    left_arduino.close()
if right_arduino:
    right_arduino.close()

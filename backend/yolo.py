#!/usr/bin/env python3
"""
YOLOv8 Directory Watcher + Segmenter (single output)
-----------------------------------------------------
- Every 6 seconds, checks tmp/ for the latest file
- Runs YOLOv8 segmentation on it
- Saves output to output.jpg
"""

import os
import time
from ultralytics import YOLO
import cv2

INPUT_DIR = "tmp"
OUTPUT_FILE = "output.jpg"
MODEL_PATH = "yolov8n-seg.pt"
CHECK_INTERVAL = 10  # seconds

def get_latest_file(directory):
    """Return the path of the latest file in the given directory, or None if empty."""
    files = [os.path.join(directory, f) for f in os.listdir(directory)]
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

def segment_image(input_path, output_path):
    """Run YOLOv8 segmentation and save result."""
    if not os.path.exists(input_path):
        print(f"❌ Input file not found: {input_path}")
        return

    model = YOLO(MODEL_PATH)
    results = model.predict(source=input_path, save=False)
    annotated_frame = results[0].plot()
    cv2.imwrite(output_path, annotated_frame)
    print(f"✅ Segmented image saved to {output_path}")

def main():
    last_processed = None
    print(f"Watching {INPUT_DIR}/ for new images every {CHECK_INTERVAL}s...")

    while True:
        latest_file = get_latest_file(INPUT_DIR)
        if latest_file and latest_file != last_processed:
            print(f"Processing: {latest_file}")
            segment_image(latest_file, OUTPUT_FILE)
            last_processed = latest_file
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()

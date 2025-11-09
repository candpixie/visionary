#!/usr/bin/env python3
"""
Visionary Terminal UI
Simple terminal-based interface for obstacle detection monitoring
"""

import asyncio
import random
from datetime import datetime
import sys
import os


class TerminalUI:
    """Terminal-based UI for Visionary detection system"""

    def __init__(self):
        self.detection_count = 0
        self.haptic_status = "READY"

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def get_zone_status(self, distance):
        """Get zone status indicator based on distance"""
        if distance is None:
            return "✅ CLEAR", ""
        elif distance < 100:
            return "🔴 DANGER", f"({distance}cm)"
        elif distance < 200:
            return "🟡 WARNING", f"({distance}cm)"
        else:
            return "✅ CLEAR", f"({distance}cm)"

    def simulate_detection(self):
        """Simulate obstacle detection"""
        left_distance = random.randint(50, 300) if random.random() > 0.7 else None
        center_distance = random.randint(50, 300) if random.random() > 0.7 else None
        right_distance = random.randint(50, 300) if random.random() > 0.7 else None

        # Determine haptic feedback
        if left_distance is not None and left_distance < 200:
            self.haptic_status = "LEFT ACTIVE"
        elif center_distance is not None and center_distance < 200:
            self.haptic_status = "CENTER ACTIVE"
        elif right_distance is not None and right_distance < 200:
            self.haptic_status = "RIGHT ACTIVE"
        else:
            self.haptic_status = "READY"

        # Increment detection count if obstacle detected
        if any(d is not None and d < 200 for d in [left_distance, center_distance, right_distance]):
            self.detection_count += 1

        return left_distance, center_distance, right_distance

    def render(self, left_dist, center_dist, right_dist):
        """Render the terminal UI"""
        self.clear_screen()

        left_status, left_info = self.get_zone_status(left_dist)
        center_status, center_info = self.get_zone_status(center_dist)
        right_status, right_info = self.get_zone_status(right_dist)

        print("=" * 60)
        print("          VISIONARY STATUS")
        print("=" * 60)
        print(f"  LEFT:   {left_status:20} {left_info}")
        print(f"  CENTER: {center_status:20} {center_info}")
        print(f"  RIGHT:  {right_status:20} {right_info}")
        print("-" * 60)
        print(f"  HAPTIC: {self.haptic_status}")
        print(f"  DETECTIONS: {self.detection_count}")
        print(f"  TIME: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        print("\n  Press Ctrl+C to exit")

    async def run(self):
        """Run the terminal UI"""
        print("Starting Visionary Terminal UI...")
        await asyncio.sleep(1)

        try:
            while True:
                left, center, right = self.simulate_detection()
                self.render(left, center, right)
                await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            self.clear_screen()
            print("\nVisionary Terminal UI stopped.")
            sys.exit(0)


async def main():
    """Main entry point"""
    ui = TerminalUI()
    await ui.run()


if __name__ == "__main__":
    asyncio.run(main())

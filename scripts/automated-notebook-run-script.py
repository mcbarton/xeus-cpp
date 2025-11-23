import subprocess
import pyautogui
import time

def main():
    pyautogui.moveTo(100, 700, duration=1)
    pyautogui.click()
    time.sleep(1)
    output_file = "screenshot.png"
    subprocess.run(["screencapture", "-C", output_file])


if __name__ == "__main__":
    main()

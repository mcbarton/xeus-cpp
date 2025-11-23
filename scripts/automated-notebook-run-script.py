import subprocess
import pyautogui
import time

def main():
    pyautogui.moveTo(150, 720, duration=1)
    pyautogui.click()
    time.sleep(1)
    pyautogui.hotkey('command', ',')
    output_file = "screenshot.png"
    subprocess.run(["screencapture", "-C", output_file])


if __name__ == "__main__":
    main()

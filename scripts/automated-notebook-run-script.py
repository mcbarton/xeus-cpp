import subprocess
import pyautogui
import time

def main():
    pyautogui.moveTo(150, 720, duration=1)
    pyautogui.click()
    time.sleep(1)
    pyautogui.moveTo(60, 10, duration=1)
    pyautogui.click()
    time.sleep(1)
    pyautogui.moveTo(60, 50, duration=1)
    pyautogui.click()
    time.sleep(1)
    output_file = "screenshot.png"
    subprocess.run(["screencapture", "-C", output_file])


if __name__ == "__main__":
    main()

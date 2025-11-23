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
    pyautogui.moveTo(75, 102, duration=1)
    pyautogui.click()
    time.sleep(1.2)
    pyautogui.moveTo(10, 20, duration=1)
    time.sleep(1.2)
    pyautogui.moveTo(700, 240, duration=1)
    pyautogui.click()
    time.sleep(1.2)
    pyautogui.moveTo(350, 630, duration=1)
    time.sleep(1.2)
    output_file = "screenshot.png"
    subprocess.run(["screencapture", "-C", output_file])


if __name__ == "__main__":
    main()

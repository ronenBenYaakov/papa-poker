import ctypes
import time
import os
import pygetwindow as gw
import pyautogui
from PIL import Image
import win32gui
import win32ui
import win32con

user32 = ctypes.windll.user32
PrintWindow = user32.PrintWindow

def capture_window(win):
    hwnd = win._hWnd if hasattr(win, "_hWnd") else win32gui.FindWindow(None, win.title)
    if not hwnd:
        print(f"[!] Cannot find hwnd for window titled: {win.title}")
        return None

    # Get window rect (includes borders)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    # Prepare device contexts
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
    saveDC.SelectObject(saveBitMap)

    # PrintWindow to capture the window contents
    result = PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    img = Image.frombuffer(
        "RGB",
        (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
        bmpstr,
        "raw",
        "BGRX",
        0,
        1,
    )

    # Cleanup
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    if result != 1:
        print(f"[!] Failed to capture window: {win.title}")
        return None

    return img

def screenshot_quarter_screen_windows(tolerance=0.2):
    screen_width, screen_height = pyautogui.size()
    screen_area = screen_width * screen_height
    target_area = screen_area * 0.25
    min_area = target_area * (1 - tolerance)
    max_area = target_area * (1 + tolerance)

    saved_paths = []
    count = 1

    for win in gw.getAllWindows():
        if not win.title or not win.visible or win.width == 0 or win.height == 0:
            continue

        area = win.width * win.height
        if min_area <= area <= max_area:
            print(f"[+] Capturing window: {win.title}")
            img = capture_window(win)
            if img is not None:
                filename = f"screenshot_{count}.png"
                img.save(filename)
                print(f"[✓] Saved screenshot: {filename}")
                saved_paths.append(os.path.abspath(filename))
                count += 1
            else:
                print(f"[!] Could not capture window: {win.title}")

    if count == 1:
        print("[!] No quarter-screen windows found to capture.")

    return saved_paths

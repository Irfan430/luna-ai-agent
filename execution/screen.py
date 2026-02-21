"""
LUNA AI Agent - Screen Vision Handler v1.0
Author: IRFAN

Provides:
  - Screen capturing (screenshot)
  - Vision analysis using multimodal LLM
  - Mouse/Keyboard control (via pyautogui)
"""

import os
import base64
import logging
import time
from typing import Dict, Any, Optional

try:
    from PIL import ImageGrab
    SCREEN_AVAILABLE = True
except ImportError:
    SCREEN_AVAILABLE = False

try:
    import pyautogui
    # Safety: slow down pyautogui
    pyautogui.PAUSE = 0.5
    pyautogui.FAILSAFE = True
    # Check if DISPLAY is available for pyautogui
    if 'DISPLAY' not in os.environ:
        PYAUTOGUI_AVAILABLE = False
    else:
        PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False

logger = logging.getLogger("luna.execution.screen")

class ScreenHandler:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.screenshot_path = "screen.png"

    def capture(self) -> str:
        """Capture screen and return absolute path."""
        if not SCREEN_AVAILABLE:
            return ""
        try:
            screenshot = ImageGrab.grab()
            screenshot.save(self.screenshot_path)
            return os.path.abspath(self.screenshot_path)
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""

    def get_base64_screenshot(self) -> Optional[str]:
        """Capture and return base64 encoded string."""
        path = self.capture()
        if not path: return None
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def execute_action(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute physical screen actions (click, type, etc)."""
        if not PYAUTOGUI_AVAILABLE:
            return {"status": "failed", "error": "Physical control (pyautogui) is not available in this environment (Headless/No X11)."}

        try:
            if action_type == "click":
                x, y = params.get("x"), params.get("y")
                if x is not None and y is not None:
                    pyautogui.click(x, y)
                    return {"status": "success", "content": f"Clicked at ({x}, {y})"}
            
            elif action_type == "type":
                text = params.get("text", "")
                pyautogui.write(text)
                return {"status": "success", "content": f"Typed: {text}"}
            
            elif action_type == "press":
                key = params.get("key", "enter")
                pyautogui.press(key)
                return {"status": "success", "content": f"Pressed: {key}"}

            elif action_type == "screenshot":
                path = self.capture()
                if path:
                    return {"status": "success", "content": f"Screenshot saved to {path}", "path": path}
                else:
                    return {"status": "failed", "error": "Failed to capture screenshot."}

            return {"status": "failed", "error": f"Unknown screen action: {action_type}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

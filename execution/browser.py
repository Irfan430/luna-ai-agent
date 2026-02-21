"""
LUNA AI Agent - Persistent Browser Worker v11.0
Author: IRFAN

Structural Stabilization Refactor:
  - Dedicated browser worker thread to avoid Playwright thread conflicts.
  - Persistent Chromium session (one launch per agent lifecycle).
  - DOM-based interaction (goto, search, click, fill, scroll).
"""

import threading
import queue
import logging
import time
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("luna.execution.browser")

class BrowserController:
    """Persistent browser controller using a dedicated worker thread."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.headless = self.config.get("browser", {}).get("headless", True)
        
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.is_running = True
        
        # Start the dedicated browser thread
        self.worker_thread = threading.Thread(target=self._browser_worker, daemon=True)
        self.worker_thread.start()

    def _browser_worker(self):
        """Dedicated thread for Playwright operations."""
        logger.info("[Browser] Worker thread started.")
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()
                logger.info("[Browser] Persistent session initialized.")
                
                while self.is_running:
                    try:
                        # Wait for requests
                        params = self.request_queue.get(timeout=1.0)
                        if params:
                            result = self._execute_in_thread(page, params)
                            self.response_queue.put(result)
                        self.request_queue.task_done()
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"[Browser] Worker Error: {e}")
                        self.response_queue.put({"status": "failed", "error": str(e)})
                
                browser.close()
            except Exception as e:
                logger.error(f"[Browser] Failed to start: {e}")
                self.is_running = False

    def _execute_in_thread(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute browser operations within the worker thread."""
        action = params.get("action", "goto")
        value = params.get("value", "")
        selector = params.get("selector", "")
        
        try:
            if action == "goto":
                if not value.startswith("http"): value = "https://" + value
                page.goto(value)
                return {"status": "success", "content": f"Navigated to {value}"}
            
            elif action == "search":
                url = f"https://www.google.com/search?q={value.replace(' ', '+')}"
                page.goto(url)
                return {"status": "success", "content": f"Searched for '{value}' on Google."}
            
            elif action == "click":
                if selector:
                    page.click(selector)
                else:
                    # Try clicking by text
                    page.click(f"text={value}")
                return {"status": "success", "content": f"Clicked '{value or selector}'"}
            
            elif action == "type" or action == "fill":
                if selector:
                    page.fill(selector, value)
                else:
                    # Try filling first input
                    page.fill("input", value)
                return {"status": "success", "content": f"Typed '{value}' into '{selector or 'input'}'"}
            
            elif action == "scroll":
                page.evaluate("window.scrollBy(0, 500)")
                return {"status": "success", "content": "Scrolled down."}
            
            elif action == "screenshot":
                path = "browser_screenshot.png"
                page.screenshot(path=path)
                return {"status": "success", "content": f"Screenshot saved to {path}"}
            
            return {"status": "failed", "error": f"Unknown browser action: {action}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to worker thread and wait for response."""
        if not self.is_running:
            return {"status": "failed", "error": "Browser worker is not running."}
        
        self.request_queue.put(params)
        # Wait for response from worker thread
        try:
            return self.response_queue.get(timeout=30)
        except queue.Empty:
            return {"status": "failed", "error": "Browser operation timed out."}

    def close(self):
        """Signal worker thread to stop."""
        self.is_running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)

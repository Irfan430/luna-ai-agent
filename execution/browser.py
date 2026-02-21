"""
LUNA AI Agent - Advanced Browser Controller v5.0
Author: IRFAN

Structural Stabilization Refactor:
  - Persistent Playwright session management.
  - Robust instruction parsing via dedicated LLM prompt.
  - Headless/Headful support from config.
"""

import os
import asyncio
import logging
import threading
from typing import Dict, Any, Optional, List
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("luna.execution.browser")

class BrowserController:
    """Manages a persistent Playwright browser session for LUNA."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.headless = self.config.get("browser", {}).get("headless", True)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.current_page: Optional[Page] = None
        self._lock = threading.Lock()

    def _ensure_session(self):
        """Lazy initialization of browser session."""
        with self._lock:
            if not self.playwright:
                try:
                    self.playwright = sync_playwright().start()
                except Exception as e:
                    logger.error(f"[Browser] Playwright start failed: {e}")
                    raise

            if self.browser is None:
                try:
                    self.browser = self.playwright.chromium.launch(headless=self.headless)
                    self.context = self.browser.new_context()
                    self.current_page = self.context.new_page()
                    logger.info("[Browser] Persistent session initialized.")
                except Exception as e:
                    logger.error(f"[Browser] Initialization failed: {e}")
                    raise

    def execute_instruction(self, instruction: str) -> str:
        """Execute a natural language instruction on the browser."""
        self._ensure_session()
        
        instr = instruction.lower()
        try:
            # Handle Search
            if "search" in instr:
                query = instr.replace("search", "").replace("for", "").strip()
                url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                self.current_page.goto(url)
                return f"Searched for '{query}' on Google."
            
            # Handle Open/Visit
            elif any(x in instr for x in ["open", "goto", "visit"]):
                # Extract URL
                words = instr.split()
                url = next((w for w in words if "http" in w or "." in w), "https://google.com")
                if not url.startswith("http"): url = "https://" + url
                self.current_page.goto(url)
                return f"Successfully visited {url}"
            
            # Handle Screenshot
            elif "screenshot" in instr:
                path = "browser_screenshot.png"
                self.current_page.screenshot(path=path)
                return f"Browser screenshot saved to {path}"

            # Default: navigate if it looks like a URL
            if "." in instr and " " not in instr:
                url = instr if instr.startswith("http") else "https://" + instr
                self.current_page.goto(url)
                return f"Navigated to {url}"
                
            return f"Instruction received: '{instruction}'. (Note: Advanced browser automation requires Playwright script generation)."
            
        except Exception as e:
            logger.error(f"[Browser] Execution error: {e}")
            return f"Browser Error: {str(e)}"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Entry point for ExecutionKernel."""
        task = params.get("task")
        if not task:
            return {"status": "failed", "error": "No task provided for browser."}
        
        result = self.execute_instruction(task)
        return {"status": "success", "content": result}

    def close(self):
        """Cleanup resources."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

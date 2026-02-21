"""
LUNA AI Agent - Playwright Browser Controller v2.0
Author: IRFAN

Structural Stabilization Refactor:
  - Robust persistent browser session management.
  - Improved natural language instruction parsing.
  - Reuse browser session, avoid relaunching.
  - Support for basic tasks: open, search, click, type, screenshot.
"""

import os
import asyncio
import logging
import threading
from typing import Dict, Any, Optional, List
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("luna.execution.browser")

class BrowserController:
    """Persistent Playwright browser controller for LUNA (Sync version for AEK)."""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: List[Page] = []
        self.current_page: Optional[Page] = None
        self._lock = threading.Lock()

    def _ensure_browser(self, headless: bool = False):
        """Ensure browser is running, reuse if exists."""
        with self._lock:
            if not self.playwright:
                self.playwright = sync_playwright().start()
            if not self.browser:
                logger.info("Launching new browser session...")
                self.browser = self.playwright.chromium.launch(headless=headless)
                self.context = self.browser.new_context()
                self.current_page = self.context.new_page()
                self.pages.append(self.current_page)
            else:
                # Check if browser is still connected
                try:
                    self.browser.version
                except:
                    logger.info("Browser disconnected, relaunching...")
                    self.browser = self.playwright.chromium.launch(headless=headless)
                    self.context = self.browser.new_context()
                    self.current_page = self.context.new_page()
                    self.pages.append(self.current_page)

    def execute_instruction(self, instruction: str) -> str:
        """Execute natural language instruction using Playwright."""
        self._ensure_browser()
        
        instr = instruction.lower()
        
        # 1. Parsing and Execution
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
                parts = instr.split()
                url = parts[-1]
                if "." not in url and len(parts) > 1:
                    # Maybe it's like "open google"
                    url = parts[-1]
                
                if not url.startswith("http"):
                    if "google" in url: url = "google.com"
                    elif "github" in url: url = "github.com"
                    url = "https://" + url
                
                self.current_page.goto(url)
                return f"Opened {url}"
            
            # Handle Click
            elif "click" in instr:
                selector = instr.replace("click", "").strip()
                # Basic selector mapping if not provided as a real selector
                if not selector.startswith((".", "#", "[")):
                    # Try to find by text
                    self.current_page.click(f"text={selector}")
                else:
                    self.current_page.click(selector)
                return f"Clicked '{selector}'"
            
            # Handle Type
            elif "type" in instr:
                # "type hello into search box"
                content = ""
                selector = "input"
                if "into" in instr:
                    parts = instr.split("into")
                    content = parts[0].replace("type", "").strip()
                    selector = parts[1].strip()
                else:
                    content = instr.replace("type", "").strip()
                
                if not selector.startswith((".", "#", "[")):
                    # Try to find input by placeholder or name if possible, or just use selector
                    self.current_page.fill(selector, content)
                else:
                    self.current_page.fill(selector, content)
                return f"Typed content into '{selector}'"
            
            # Handle Screenshot
            elif "screenshot" in instr:
                path = "browser_screenshot.png"
                self.current_page.screenshot(path=path)
                return f"Browser screenshot saved to {path}"
            
            # Handle Scroll
            elif "scroll" in instr:
                self.current_page.evaluate("window.scrollBy(0, 500)")
                return "Scrolled down the page."
            
            else:
                # Default: try to treat as URL if it looks like one
                if "." in instr and " " not in instr:
                    url = instr if instr.startswith("http") else "https://" + instr
                    self.current_page.goto(url)
                    return f"Opened {url}"
                
                return f"Instruction '{instruction}' recognized but no specific handler matched. Attempting to search..."
                
        except Exception as e:
            logger.error(f"Browser instruction error: {e}")
            return f"Error executing browser task: {str(e)}"

    def close(self):
        """Clean up browser resources."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

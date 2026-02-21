"""
LUNA AI Agent - Playwright Browser Controller v1.0
Author: IRFAN

Phase 3: Playwright Full Feature Enable
  - Persistent browser session.
  - Multi-tab support.
  - Natural language task instructions.
  - Screenshot, click, type, scroll.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("luna.execution.browser")

class BrowserController:
    """Persistent Playwright browser controller for LUNA."""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: List[Page] = []
        self.current_page: Optional[Page] = None
        self._loop = asyncio.new_event_loop()

    async def _ensure_browser(self, headless: bool = False):
        if not self.playwright:
            self.playwright = await async_playwright().start()
        if not self.browser:
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.context = await self.browser.new_context()
            self.current_page = await self.context.new_page()
            self.pages.append(self.current_page)

    def execute_instruction(self, instruction: str) -> str:
        """Execute natural language instruction using Playwright."""
        # This would ideally use an LLM to translate instruction to Playwright code
        # For now, we'll implement basic routing for common instructions
        return self._run_async(self._handle_instruction(instruction))

    async def _handle_instruction(self, instruction: str) -> str:
        await self._ensure_browser()
        
        instr = instruction.lower()
        if "open" in instr or "goto" in instr or "visit" in instr:
            url = instr.split(" ")[-1]
            if not url.startswith("http"): url = "https://" + url
            await self.current_page.goto(url)
            return f"Opened {url}"
        
        elif "click" in instr:
            selector = instr.split("click")[-1].strip()
            await self.current_page.click(selector)
            return f"Clicked {selector}"
        
        elif "type" in instr:
            parts = instr.split("type")[-1].strip().split("into")
            text = parts[0].strip()
            selector = parts[1].strip() if len(parts) > 1 else "input"
            await self.current_page.fill(selector, text)
            return f"Typed '{text}' into {selector}"
        
        elif "screenshot" in instr:
            path = "screenshot.png"
            await self.current_page.screenshot(path=path)
            return f"Screenshot saved to {path}"
        
        elif "scroll" in instr:
            await self.current_page.evaluate("window.scrollBy(0, 500)")
            return "Scrolled down"
        
        return f"Instruction '{instruction}' not yet implemented in basic controller."

    def _run_async(self, coro):
        return self._loop.run_until_complete(coro)

    def close(self):
        if self.browser:
            self._run_async(self.browser.close())
        if self.playwright:
            self._run_async(self.playwright.stop())

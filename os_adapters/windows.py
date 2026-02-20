"""
LUNA AI Agent - Windows OS Adapter
Author: IRFAN
"""

import subprocess
import os
import psutil
import webbrowser

class WindowsAdapter:
    """Windows-specific OS operations."""

    def open_application(self, app: str, args: list = None) -> bool:
        try:
            cmd = ['start', app] + (args if args else [])
            subprocess.Popen(cmd, shell=True)
            return True
        except Exception:
            return False

    def close_application(self, name: str) -> bool:
        try:
            subprocess.run(['taskkill', '/F', '/IM', f"{name}.exe"], check=True)
            return True
        except Exception:
            return False

    def focus_window(self, window_title: str) -> bool:
        # Requires pywin32 or similar, but for now we use a simple shell command
        try:
            # Placeholder for Windows window focus
            return False
        except Exception:
            return False

    def run_command(self, command: str, cwd: str = None) -> str:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return str(e)

    def list_processes(self) -> list:
        return [proc.info for proc in psutil.process_iter(['pid', 'name', 'username'])]

    def media_control(self, action: str) -> bool:
        # Windows media control via shell keys or specialized libraries
        return False

    def open_url(self, url: str, browser: str = None) -> bool:
        try:
            if browser:
                subprocess.Popen(['start', browser, url], shell=True)
            else:
                webbrowser.open(url)
            return True
        except Exception:
            return False

    def browser_search(self, query: str, browser: str = None) -> bool:
        url = f"https://www.google.com/search?q={query}"
        return self.open_url(url, browser)

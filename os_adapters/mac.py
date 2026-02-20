"""
LUNA AI Agent - macOS OS Adapter
Author: IRFAN
"""

import subprocess
import os
import psutil
import webbrowser

class MacAdapter:
    """macOS-specific OS operations."""

    def open_application(self, app: str, args: list = None) -> bool:
        try:
            cmd = ['open', '-a', app] + (args if args else [])
            subprocess.Popen(cmd)
            return True
        except Exception:
            return False

    def close_application(self, name: str) -> bool:
        try:
            subprocess.run(['pkill', '-i', name], check=True)
            return True
        except Exception:
            return False

    def focus_window(self, window_title: str) -> bool:
        try:
            # AppleScript for window focus
            script = f'tell application "System Events" to set frontmost of process "{window_title}" to true'
            subprocess.run(['osascript', '-e', script], check=True)
            return True
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
        try:
            # AppleScript for media control
            scripts = {
                "play": 'tell application "Music" to play',
                "pause": 'tell application "Music" to pause',
                "next": 'tell application "Music" to next track',
                "previous": 'tell application "Music" to previous track'
            }
            if action in scripts:
                subprocess.run(['osascript', '-e', scripts[action]], check=True)
                return True
            return False
        except Exception:
            return False

    def open_url(self, url: str, browser: str = None) -> bool:
        try:
            if browser:
                subprocess.Popen(['open', '-a', browser, url])
            else:
                webbrowser.open(url)
            return True
        except Exception:
            return False

    def browser_search(self, query: str, browser: str = None) -> bool:
        url = f"https://www.google.com/search?q={query}"
        return self.open_url(url, browser)

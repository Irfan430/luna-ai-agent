"""
LUNA AI Agent - Linux OS Adapter
Author: IRFAN
"""

import subprocess
import os
import psutil
import webbrowser

class LinuxAdapter:
    """Linux-specific OS operations."""

    def open_application(self, app: str, args: list = None) -> bool:
        try:
            cmd = [app] + (args if args else [])
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def close_application(self, name: str) -> bool:
        try:
            for proc in psutil.process_iter(['name']):
                if name.lower() in proc.info['name'].lower():
                    proc.terminate()
            return True
        except Exception:
            return False

    def focus_window(self, window_title: str) -> bool:
        try:
            # Requires xdotool
            subprocess.run(['xdotool', 'search', '--name', window_title, 'windowactivate'], check=True)
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
            # Requires playerctl
            actions = {"play": "play", "pause": "pause", "next": "next", "previous": "previous"}
            if action in actions:
                subprocess.run(['playerctl', actions[action]], check=True)
                return True
            return False
        except Exception:
            return False

    def open_url(self, url: str, browser: str = None) -> bool:
        try:
            if browser:
                # Try to find the browser executable
                subprocess.Popen([browser, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                webbrowser.open(url)
            return True
        except Exception:
            return False

    def browser_search(self, query: str, browser: str = None) -> bool:
        url = f"https://www.google.com/search?q={query}"
        return self.open_url(url, browser)

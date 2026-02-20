"""
LUNA AI Agent - App Launcher
Author: IRFAN

Launch system applications.
"""

import subprocess
import platform
from typing import Optional
from core.task_result import TaskResult


class AppLauncher:
    """Launch system applications."""
    
    def __init__(self):
        """Initialize app launcher."""
        self.system = platform.system()
    
    def launch(self, app_name: str, args: Optional[str] = None) -> TaskResult:
        """
        Launch application.
        
        Args:
            app_name: Application name or path
            args: Optional arguments
            
        Returns:
            TaskResult
        """
        try:
            command = [app_name]
            if args:
                command.extend(args.split())
            
            # Launch app without blocking
            if self.system == "Windows":
                subprocess.Popen(command, shell=True)
            else:
                subprocess.Popen(command, stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
            
            return TaskResult.success(
                content=f"Launched application: {app_name}",
                confidence=0.9,
                verified=False,  # Can't easily verify app launched
                execution_used=True,
                risk_level="low"
            )
            
        except Exception as e:
            return TaskResult.failed(
                error=f"Failed to launch {app_name}: {str(e)}",
                content=""
            )
    
    def open_file(self, file_path: str) -> TaskResult:
        """
        Open file with default application.
        
        Args:
            file_path: Path to file
            
        Returns:
            TaskResult
        """
        try:
            if self.system == "Windows":
                subprocess.Popen(['start', file_path], shell=True)
            elif self.system == "Darwin":  # macOS
                subprocess.Popen(['open', file_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', file_path])
            
            return TaskResult.success(
                content=f"Opened file: {file_path}",
                confidence=0.9,
                verified=False,
                execution_used=True,
                risk_level="low"
            )
            
        except Exception as e:
            return TaskResult.failed(
                error=f"Failed to open file {file_path}: {str(e)}",
                content=""
            )
    
    def open_url(self, url: str) -> TaskResult:
        """
        Open URL in default browser.
        
        Args:
            url: URL to open
            
        Returns:
            TaskResult
        """
        import webbrowser
        
        try:
            webbrowser.open(url)
            
            return TaskResult.success(
                content=f"Opened URL: {url}",
                confidence=0.9,
                verified=False,
                execution_used=True,
                risk_level="low"
            )
            
        except Exception as e:
            return TaskResult.failed(
                error=f"Failed to open URL {url}: {str(e)}",
                content=""
            )

"""
LUNA AI Agent - File Manager
Author: IRFAN

File operations with validation.
"""

import os
import shutil
from typing import Optional
from core.task_result import TaskResult


class FileManager:
    """Manage file operations safely."""
    
    def __init__(self):
        """Initialize file manager."""
        pass
    
    def create_file(self, path: str, content: str = "") -> TaskResult:
        """
        Create a new file.
        
        Args:
            path: File path
            content: File content
            
        Returns:
            TaskResult
        """
        try:
            # Create directory if needed
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Create file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Verify file was created
            if os.path.exists(path):
                return TaskResult.success(
                    content=f"File created: {path}",
                    confidence=1.0,
                    verified=True,
                    execution_used=True,
                    risk_level="low"
                )
            else:
                return TaskResult.failed(
                    error=f"File creation verification failed: {path}",
                    content=""
                )
                
        except Exception as e:
            return TaskResult.failed(
                error=f"File creation error: {str(e)}",
                content=""
            )
    
    def read_file(self, path: str) -> TaskResult:
        """
        Read file content.
        
        Args:
            path: File path
            
        Returns:
            TaskResult with file content
        """
        try:
            if not os.path.exists(path):
                return TaskResult.failed(
                    error=f"File not found: {path}",
                    content=""
                )
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return TaskResult.success(
                content=content,
                confidence=1.0,
                verified=True,
                execution_used=False,
                risk_level="low"
            )
            
        except Exception as e:
            return TaskResult.failed(
                error=f"File read error: {str(e)}",
                content=""
            )
    
    def edit_file(self, path: str, content: str) -> TaskResult:
        """
        Edit existing file.
        
        Args:
            path: File path
            content: New content
            
        Returns:
            TaskResult
        """
        try:
            if not os.path.exists(path):
                return TaskResult.failed(
                    error=f"File not found: {path}",
                    content=""
                )
            
            # Backup original content
            with open(path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Write new content
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Verify edit
            with open(path, 'r', encoding='utf-8') as f:
                new_content = f.read()
            
            if new_content == content:
                return TaskResult.success(
                    content=f"File edited: {path}",
                    confidence=1.0,
                    verified=True,
                    execution_used=True,
                    risk_level="medium"
                )
            else:
                # Restore original content
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                return TaskResult.failed(
                    error=f"File edit verification failed: {path}",
                    content=""
                )
                
        except Exception as e:
            return TaskResult.failed(
                error=f"File edit error: {str(e)}",
                content=""
            )
    
    def delete_file(self, path: str) -> TaskResult:
        """
        Delete file.
        
        Args:
            path: File path
            
        Returns:
            TaskResult
        """
        try:
            if not os.path.exists(path):
                return TaskResult.failed(
                    error=f"File not found: {path}",
                    content=""
                )
            
            os.remove(path)
            
            # Verify deletion
            if not os.path.exists(path):
                return TaskResult.success(
                    content=f"File deleted: {path}",
                    confidence=1.0,
                    verified=True,
                    execution_used=True,
                    risk_level="high"
                )
            else:
                return TaskResult.failed(
                    error=f"File deletion verification failed: {path}",
                    content=""
                )
                
        except Exception as e:
            return TaskResult.failed(
                error=f"File deletion error: {str(e)}",
                content=""
            )
    
    def move_file(self, src: str, dst: str) -> TaskResult:
        """
        Move/rename file.
        
        Args:
            src: Source path
            dst: Destination path
            
        Returns:
            TaskResult
        """
        try:
            if not os.path.exists(src):
                return TaskResult.failed(
                    error=f"Source file not found: {src}",
                    content=""
                )
            
            # Create destination directory if needed
            dst_dir = os.path.dirname(dst)
            if dst_dir and not os.path.exists(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)
            
            shutil.move(src, dst)
            
            # Verify move
            if os.path.exists(dst) and not os.path.exists(src):
                return TaskResult.success(
                    content=f"File moved: {src} -> {dst}",
                    confidence=1.0,
                    verified=True,
                    execution_used=True,
                    risk_level="medium"
                )
            else:
                return TaskResult.failed(
                    error=f"File move verification failed: {src} -> {dst}",
                    content=""
                )
                
        except Exception as e:
            return TaskResult.failed(
                error=f"File move error: {str(e)}",
                content=""
            )

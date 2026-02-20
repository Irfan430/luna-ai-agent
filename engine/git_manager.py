"""
LUNA AI Agent - Git Manager
Author: IRFAN

Git operations with validation.
"""

import os
from typing import Optional, List
from .command_runner import CommandRunner
from core.task_result import TaskResult


class GitManager:
    """Manage git operations safely."""
    
    def __init__(self):
        """Initialize git manager."""
        self.command_runner = CommandRunner()
    
    def init(self, path: str) -> TaskResult:
        """
        Initialize git repository.
        
        Args:
            path: Repository path
            
        Returns:
            TaskResult
        """
        return self.command_runner.run(f"git init", cwd=path)
    
    def clone(self, url: str, path: Optional[str] = None) -> TaskResult:
        """
        Clone repository.
        
        Args:
            url: Repository URL
            path: Destination path (optional)
            
        Returns:
            TaskResult
        """
        command = f"git clone {url}"
        if path:
            command += f" {path}"
        
        return self.command_runner.run(command)
    
    def add(self, files: str = ".", cwd: Optional[str] = None) -> TaskResult:
        """
        Stage files for commit.
        
        Args:
            files: Files to stage (default: all)
            cwd: Repository path
            
        Returns:
            TaskResult
        """
        return self.command_runner.run(f"git add {files}", cwd=cwd)
    
    def commit(self, message: str, cwd: Optional[str] = None) -> TaskResult:
        """
        Commit staged changes.
        
        Args:
            message: Commit message
            cwd: Repository path
            
        Returns:
            TaskResult
        """
        # Format as semantic commit if not already
        if not any(message.startswith(prefix) for prefix in 
                  ["feat:", "fix:", "docs:", "style:", "refactor:", "test:", "chore:"]):
            message = f"chore: {message}"
        
        return self.command_runner.run(f'git commit -m "{message}"', cwd=cwd)
    
    def push(self, remote: str = "origin", branch: Optional[str] = None, 
             cwd: Optional[str] = None) -> TaskResult:
        """
        Push commits to remote.
        
        Args:
            remote: Remote name
            branch: Branch name (optional)
            cwd: Repository path
            
        Returns:
            TaskResult
        """
        command = f"git push {remote}"
        if branch:
            command += f" {branch}"
        
        result = self.command_runner.run(command, cwd=cwd)
        
        # Mark as high risk
        if result.status == "success":
            result.risk_level = "high"
        
        return result
    
    def pull(self, remote: str = "origin", branch: Optional[str] = None,
             cwd: Optional[str] = None) -> TaskResult:
        """
        Pull changes from remote.
        
        Args:
            remote: Remote name
            branch: Branch name (optional)
            cwd: Repository path
            
        Returns:
            TaskResult
        """
        command = f"git pull {remote}"
        if branch:
            command += f" {branch}"
        
        return self.command_runner.run(command, cwd=cwd)
    
    def status(self, cwd: Optional[str] = None) -> TaskResult:
        """
        Get repository status.
        
        Args:
            cwd: Repository path
            
        Returns:
            TaskResult with status output
        """
        return self.command_runner.run("git status", cwd=cwd)
    
    def branch(self, name: Optional[str] = None, cwd: Optional[str] = None) -> TaskResult:
        """
        Create or list branches.
        
        Args:
            name: Branch name to create (optional)
            cwd: Repository path
            
        Returns:
            TaskResult
        """
        if name:
            return self.command_runner.run(f"git branch {name}", cwd=cwd)
        else:
            return self.command_runner.run("git branch", cwd=cwd)
    
    def checkout(self, branch: str, create: bool = False, 
                cwd: Optional[str] = None) -> TaskResult:
        """
        Switch branches.
        
        Args:
            branch: Branch name
            create: Create new branch if True
            cwd: Repository path
            
        Returns:
            TaskResult
        """
        command = "git checkout"
        if create:
            command += " -b"
        command += f" {branch}"
        
        return self.command_runner.run(command, cwd=cwd)
    
    def add_commit_push(self, message: str, files: str = ".", 
                       remote: str = "origin", branch: Optional[str] = None,
                       cwd: Optional[str] = None) -> TaskResult:
        """
        Convenience method: add, commit, and push in one operation.
        
        Args:
            message: Commit message
            files: Files to stage
            remote: Remote name
            branch: Branch name (optional)
            cwd: Repository path
            
        Returns:
            TaskResult
        """
        # Add files
        add_result = self.add(files, cwd)
        if add_result.status == "failed":
            return add_result
        
        # Commit
        commit_result = self.commit(message, cwd)
        if commit_result.status == "failed":
            return commit_result
        
        # Push
        push_result = self.push(remote, branch, cwd)
        
        return push_result

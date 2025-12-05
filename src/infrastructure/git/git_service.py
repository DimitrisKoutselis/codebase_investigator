import os
import asyncio
from pathlib import Path
from typing import List

from git import Repo

from src.domain.value_objects.repo_url import RepoURL
from src.application.interfaces.i_git_service import IGitService


class GitService(IGitService):
    """Concrete implementation of Git operations using GitPython."""

    SUPPORTED_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".html",
        ".css",
        ".scss",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".sh",
        ".bash",
        ".zsh",
        ".sql",
        ".graphql",
        ".dockerfile",
        ".toml",
        ".ini",
        ".cfg",
    }

    IGNORED_DIRS = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
    }

    async def clone_repository(self, repo_url: RepoURL, target_path: str) -> str:
        """Clone a repository to the target path."""
        # Run git clone in a thread pool to not block
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: Repo.clone_from(repo_url.clone_url, target_path, depth=1)
        )
        return target_path

    async def list_files(
        self, local_path: str, extensions: List[str] | None = None
    ) -> List[str]:
        """List all relevant files in the repository."""
        valid_extensions = set(extensions) if extensions else self.SUPPORTED_EXTENSIONS
        files = []

        base_path = Path(local_path)

        for root, dirs, filenames in os.walk(base_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

            for filename in filenames:
                file_path = Path(root) / filename
                if file_path.suffix.lower() in valid_extensions:
                    # Return relative path from base
                    relative_path = file_path.relative_to(base_path)
                    files.append(str(relative_path))

        return files

    async def read_file(self, local_path: str, file_path: str) -> str:
        """Read the contents of a file."""
        full_path = Path(local_path) / file_path

        # Read in thread pool
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None, lambda: full_path.read_text(encoding="utf-8", errors="ignore")
        )
        return content

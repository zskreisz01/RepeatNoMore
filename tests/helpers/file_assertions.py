"""File content assertion utilities for testing."""

import re
from pathlib import Path
from typing import Optional


class FileAssertions:
    """Utility class for asserting file contents in tests."""

    @staticmethod
    def assert_file_exists(path: Path, message: str = "") -> None:
        """
        Assert that a file exists.

        Args:
            path: Path to the file
            message: Optional additional message

        Raises:
            AssertionError: If file doesn't exist
        """
        assert path.exists(), f"File {path} should exist. {message}"

    @staticmethod
    def assert_file_not_exists(path: Path, message: str = "") -> None:
        """
        Assert that a file does not exist.

        Args:
            path: Path to the file
            message: Optional additional message

        Raises:
            AssertionError: If file exists
        """
        assert not path.exists(), f"File {path} should not exist. {message}"

    @staticmethod
    def assert_file_contains(path: Path, content: str) -> None:
        """
        Assert that file contains specific content.

        Args:
            path: Path to the file
            content: Content that should be in the file

        Raises:
            AssertionError: If file doesn't exist or content not found
        """
        FileAssertions.assert_file_exists(path)
        file_content = path.read_text(encoding="utf-8")
        assert content in file_content, (
            f"File {path} should contain '{content[:100]}...'"
        )

    @staticmethod
    def assert_file_not_contains(path: Path, content: str) -> None:
        """
        Assert that file does not contain specific content.

        Args:
            path: Path to the file
            content: Content that should not be in the file

        Raises:
            AssertionError: If content is found
        """
        FileAssertions.assert_file_exists(path)
        file_content = path.read_text(encoding="utf-8")
        assert content not in file_content, (
            f"File {path} should not contain '{content[:100]}...'"
        )

    @staticmethod
    def assert_file_contains_pattern(path: Path, pattern: str) -> None:
        """
        Assert that file contains content matching regex pattern.

        Args:
            path: Path to the file
            pattern: Regex pattern to match

        Raises:
            AssertionError: If pattern not found
        """
        FileAssertions.assert_file_exists(path)
        file_content = path.read_text(encoding="utf-8")
        assert re.search(pattern, file_content), (
            f"File {path} should match pattern '{pattern}'"
        )

    @staticmethod
    def assert_file_has_sections(path: Path, sections: list[str]) -> None:
        """
        Assert that file has markdown sections with given headings.

        Args:
            path: Path to the file
            sections: List of section headings to find

        Raises:
            AssertionError: If any section is missing
        """
        FileAssertions.assert_file_exists(path)
        content = path.read_text(encoding="utf-8")
        for section in sections:
            has_section = (
                f"## {section}" in content
                or f"### {section}" in content
                or f"# {section}" in content
            )
            assert has_section, f"File {path} should have section '{section}'"

    @staticmethod
    def get_section_content(path: Path, section_heading: str) -> Optional[str]:
        """
        Extract content of a specific markdown section.

        Args:
            path: Path to the file
            section_heading: The section heading to find

        Returns:
            Content of the section or None if not found
        """
        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")
        pattern = rf"#{2,3} {re.escape(section_heading)}\n(.*?)(?=\n#{2,3} |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    @staticmethod
    def get_file_content(path: Path) -> str:
        """
        Get the full content of a file.

        Args:
            path: Path to the file

        Returns:
            File content as string

        Raises:
            AssertionError: If file doesn't exist
        """
        FileAssertions.assert_file_exists(path)
        return path.read_text(encoding="utf-8")

    @staticmethod
    def count_occurrences(path: Path, text: str) -> int:
        """
        Count occurrences of text in file.

        Args:
            path: Path to the file
            text: Text to count

        Returns:
            Number of occurrences
        """
        if not path.exists():
            return 0
        content = path.read_text(encoding="utf-8")
        return content.count(text)

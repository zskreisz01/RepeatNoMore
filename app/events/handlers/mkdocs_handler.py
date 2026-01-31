"""MkDocs navigation handler for document events."""

from pathlib import Path
from typing import Optional
import yaml

from app.config import get_settings
from app.events.types import DocumentEvent, EventData
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Paths to exclude from mkdocs navigation
EXCLUDED_PATHS = [
    "drafts/",
    "qa/accepted_qa",
    "suggestions/",
]


class MkDocsHandler:
    """
    Handler for updating mkdocs.yml navigation when documents change.

    Automatically updates the nav structure when docs are added, removed,
    or renamed. Excludes draft and pending Q&A files from navigation.
    """

    def __init__(self, mkdocs_path: Optional[str] = None):
        """
        Initialize the MkDocs handler.

        Args:
            mkdocs_path: Optional path to mkdocs.yml. Defaults to project path.
        """
        settings = get_settings()
        if mkdocs_path:
            self.mkdocs_path = Path(mkdocs_path)
        else:
            # Default to knowledge_base mkdocs.yml (if exists)
            base_path = Path(settings.docs_repo_path)
            self.mkdocs_path = base_path / "mkdocs.yml"

        logger.info("mkdocs_handler_initialized", path=str(self.mkdocs_path))

    async def handle_event(self, event: EventData) -> None:
        """
        Handle document-related events.

        Args:
            event: The event data
        """
        if event.event_type not in [
            DocumentEvent.DOC_CREATED,
            DocumentEvent.DOC_UPDATED,
            DocumentEvent.DOC_DELETED,
            DocumentEvent.DRAFT_APPROVED,
            DocumentEvent.QUESTION_ANSWERED,
        ]:
            return

        # Skip if file is in excluded paths
        if event.file_path and self._is_excluded(event.file_path):
            logger.debug(
                "skipping_excluded_path",
                path=event.file_path,
                event_type=event.event_type.value,
            )
            return

        await self._update_navigation(event)

    def _is_excluded(self, file_path: str) -> bool:
        """Check if a file path should be excluded from navigation."""
        for excluded in EXCLUDED_PATHS:
            if excluded in file_path:
                return True
        return False

    async def _update_navigation(self, event: EventData) -> None:
        """
        Update mkdocs.yml navigation based on the event.

        Args:
            event: The event data containing file path information
        """
        if not self.mkdocs_path.exists():
            logger.warning("mkdocs_file_not_found", path=str(self.mkdocs_path))
            return

        try:
            # Load current mkdocs.yml
            with open(self.mkdocs_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config:
                logger.warning("mkdocs_config_empty")
                return

            nav = config.get("nav", [])
            if not nav:
                logger.debug("mkdocs_no_nav_section")
                return

            # Determine action based on event type
            file_path = event.file_path
            if not file_path:
                return

            updated = False

            if event.event_type == DocumentEvent.DOC_CREATED:
                updated = self._add_to_nav(nav, file_path, event.metadata)
            elif event.event_type == DocumentEvent.DOC_DELETED:
                updated = self._remove_from_nav(nav, file_path)
            elif event.event_type in [
                DocumentEvent.DRAFT_APPROVED,
                DocumentEvent.QUESTION_ANSWERED,
            ]:
                # For approved drafts/answered questions, add to nav if not present
                updated = self._add_to_nav(nav, file_path, event.metadata)

            if updated:
                config["nav"] = nav
                with open(self.mkdocs_path, "w", encoding="utf-8") as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                logger.info(
                    "mkdocs_nav_updated",
                    file_path=file_path,
                    event_type=event.event_type.value,
                )

        except Exception as e:
            logger.error(
                "mkdocs_update_failed",
                error=str(e),
                file_path=event.file_path,
            )

    def _add_to_nav(
        self,
        nav: list,
        file_path: str,
        metadata: dict,
    ) -> bool:
        """
        Add a file to the navigation structure.

        Args:
            nav: The navigation list to modify
            file_path: Path to the file to add
            metadata: Additional metadata (may contain nav_section)

        Returns:
            True if navigation was modified
        """
        # Extract relative path and title
        path = Path(file_path)
        title = metadata.get("title", path.stem.replace("_", " ").title())
        nav_section = metadata.get("nav_section")

        # Check if already in nav
        if self._find_in_nav(nav, file_path):
            return False

        # If section specified, find and add to it
        if nav_section:
            for item in nav:
                if isinstance(item, dict):
                    section_name = list(item.keys())[0]
                    if section_name.lower() == nav_section.lower():
                        item[section_name].append({title: str(path)})
                        return True

        # Otherwise, append to root
        nav.append({title: str(path)})
        return True

    def _remove_from_nav(self, nav: list, file_path: str) -> bool:
        """
        Remove a file from the navigation structure.

        Args:
            nav: The navigation list to modify
            file_path: Path to the file to remove

        Returns:
            True if navigation was modified
        """
        for i, item in enumerate(nav):
            if isinstance(item, dict):
                for section_name, section_items in item.items():
                    if isinstance(section_items, list):
                        for j, section_item in enumerate(section_items):
                            if isinstance(section_item, dict):
                                for title, path in section_item.items():
                                    if path == file_path:
                                        del section_items[j]
                                        return True
                            elif section_item == file_path:
                                del section_items[j]
                                return True
            elif item == file_path:
                del nav[i]
                return True
        return False

    def _find_in_nav(self, nav: list, file_path: str) -> bool:
        """Check if a file path is already in the navigation."""
        for item in nav:
            if isinstance(item, dict):
                for section_name, section_items in item.items():
                    if isinstance(section_items, list):
                        for section_item in section_items:
                            if isinstance(section_item, dict):
                                for title, path in section_item.items():
                                    if path == file_path:
                                        return True
                            elif section_item == file_path:
                                return True
                    elif section_items == file_path:
                        return True
            elif item == file_path:
                return True
        return False

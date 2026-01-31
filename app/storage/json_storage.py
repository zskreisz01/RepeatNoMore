"""JSON file-based storage implementation."""

import json
import fcntl
from pathlib import Path
from typing import Any, TypeVar, Generic
from datetime import datetime

from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class JSONStorage(Generic[T]):
    """Thread-safe JSON file storage with file locking."""

    def __init__(self, file_path: str | Path, collection_name: str = "items"):
        """
        Initialize JSON storage.

        Args:
            file_path: Path to the JSON file
            collection_name: Name of the collection in the JSON structure
        """
        self.file_path = Path(file_path)
        self.collection_name = collection_name
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure the storage file and directory exist."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write_data({
                self.collection_name: [],
                "metadata": {
                    "created_at": datetime.utcnow().isoformat(),
                    "last_updated": datetime.utcnow().isoformat(),
                    "version": 1
                }
            })
            logger.info("storage_file_created", path=str(self.file_path))

    def _read_data(self) -> dict[str, Any]:
        """Read data from file with file locking."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return data
        except json.JSONDecodeError as e:
            logger.error("storage_read_error", path=str(self.file_path), error=str(e))
            return {self.collection_name: [], "metadata": {}}
        except Exception as e:
            logger.error("storage_read_error", path=str(self.file_path), error=str(e))
            raise

    def _write_data(self, data: dict[str, Any]) -> None:
        """Write data to file with file locking."""
        try:
            data["metadata"]["last_updated"] = datetime.utcnow().isoformat()
            with open(self.file_path, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error("storage_write_error", path=str(self.file_path), error=str(e))
            raise

    def get_all(self) -> list[dict[str, Any]]:
        """Get all items from storage."""
        data = self._read_data()
        return data.get(self.collection_name, [])

    def get_by_id(self, item_id: str) -> dict[str, Any] | None:
        """Get item by ID."""
        items = self.get_all()
        for item in items:
            if item.get("id") == item_id:
                return item
        return None

    def add(self, item: dict[str, Any]) -> dict[str, Any]:
        """Add a new item to storage."""
        data = self._read_data()
        items = data.get(self.collection_name, [])
        items.append(item)
        data[self.collection_name] = items
        self._write_data(data)
        logger.info("storage_item_added", collection=self.collection_name, id=item.get("id"))
        return item

    def update(self, item_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update an existing item."""
        data = self._read_data()
        items = data.get(self.collection_name, [])

        for i, item in enumerate(items):
            if item.get("id") == item_id:
                items[i] = {**item, **updates}
                items[i]["updated_at"] = datetime.utcnow().isoformat()
                data[self.collection_name] = items
                self._write_data(data)
                logger.info("storage_item_updated", collection=self.collection_name, id=item_id)
                return items[i]

        logger.warning("storage_item_not_found", collection=self.collection_name, id=item_id)
        return None

    def delete(self, item_id: str) -> bool:
        """Delete an item by ID."""
        data = self._read_data()
        items = data.get(self.collection_name, [])
        original_count = len(items)

        items = [item for item in items if item.get("id") != item_id]

        if len(items) < original_count:
            data[self.collection_name] = items
            self._write_data(data)
            logger.info("storage_item_deleted", collection=self.collection_name, id=item_id)
            return True

        logger.warning("storage_item_not_found", collection=self.collection_name, id=item_id)
        return False

    def query(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Query items with filters."""
        items = self.get_all()
        result = []

        for item in items:
            match = True
            for key, value in filters.items():
                if item.get(key) != value:
                    match = False
                    break
            if match:
                result.append(item)

        return result

    def count(self) -> int:
        """Get total item count."""
        return len(self.get_all())

    def clear(self) -> None:
        """Clear all items from storage."""
        data = self._read_data()
        data[self.collection_name] = []
        self._write_data(data)
        logger.info("storage_cleared", collection=self.collection_name)

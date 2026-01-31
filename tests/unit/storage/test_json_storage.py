"""Unit tests for JSON storage."""

import pytest
import json
from pathlib import Path

from app.storage.json_storage import JSONStorage


class TestJSONStorage:
    """Tests for JSONStorage class."""

    @pytest.fixture
    def storage_path(self, tmp_path: Path) -> Path:
        """Create a temporary storage path."""
        return tmp_path / "test_storage.json"

    @pytest.fixture
    def storage(self, storage_path: Path) -> JSONStorage:
        """Create a storage instance."""
        return JSONStorage(storage_path, collection_name="items")

    def test_creates_file_on_init(self, storage_path: Path):
        """Test that storage file is created on initialization."""
        assert not storage_path.exists()
        JSONStorage(storage_path, collection_name="items")
        assert storage_path.exists()

    def test_initial_file_structure(self, storage_path: Path):
        """Test initial file structure."""
        JSONStorage(storage_path, collection_name="items")
        with open(storage_path) as f:
            data = json.load(f)
        assert "items" in data
        assert data["items"] == []
        assert "metadata" in data
        assert "created_at" in data["metadata"]

    def test_add_item(self, storage: JSONStorage):
        """Test adding an item."""
        item = {"id": "test-1", "name": "Test Item"}
        result = storage.add(item)
        assert result == item
        assert storage.count() == 1

    def test_get_all(self, storage: JSONStorage):
        """Test getting all items."""
        storage.add({"id": "1", "name": "Item 1"})
        storage.add({"id": "2", "name": "Item 2"})
        items = storage.get_all()
        assert len(items) == 2

    def test_get_by_id(self, storage: JSONStorage):
        """Test getting item by ID."""
        storage.add({"id": "test-1", "name": "Test Item"})
        item = storage.get_by_id("test-1")
        assert item is not None
        assert item["name"] == "Test Item"

    def test_get_by_id_not_found(self, storage: JSONStorage):
        """Test getting non-existent item."""
        item = storage.get_by_id("non-existent")
        assert item is None

    def test_update_item(self, storage: JSONStorage):
        """Test updating an item."""
        storage.add({"id": "test-1", "name": "Original"})
        result = storage.update("test-1", {"name": "Updated"})
        assert result is not None
        assert result["name"] == "Updated"
        assert "updated_at" in result

    def test_update_item_not_found(self, storage: JSONStorage):
        """Test updating non-existent item."""
        result = storage.update("non-existent", {"name": "Updated"})
        assert result is None

    def test_delete_item(self, storage: JSONStorage):
        """Test deleting an item."""
        storage.add({"id": "test-1", "name": "Test Item"})
        assert storage.count() == 1
        result = storage.delete("test-1")
        assert result is True
        assert storage.count() == 0

    def test_delete_item_not_found(self, storage: JSONStorage):
        """Test deleting non-existent item."""
        result = storage.delete("non-existent")
        assert result is False

    def test_query_with_filters(self, storage: JSONStorage):
        """Test querying with filters."""
        storage.add({"id": "1", "status": "active", "type": "A"})
        storage.add({"id": "2", "status": "active", "type": "B"})
        storage.add({"id": "3", "status": "inactive", "type": "A"})

        # Single filter
        active = storage.query({"status": "active"})
        assert len(active) == 2

        # Multiple filters
        active_a = storage.query({"status": "active", "type": "A"})
        assert len(active_a) == 1
        assert active_a[0]["id"] == "1"

    def test_count(self, storage: JSONStorage):
        """Test counting items."""
        assert storage.count() == 0
        storage.add({"id": "1"})
        assert storage.count() == 1
        storage.add({"id": "2"})
        assert storage.count() == 2

    def test_clear(self, storage: JSONStorage):
        """Test clearing all items."""
        storage.add({"id": "1"})
        storage.add({"id": "2"})
        assert storage.count() == 2
        storage.clear()
        assert storage.count() == 0

    def test_persistence(self, storage_path: Path):
        """Test that data persists across instances."""
        # Create and populate storage
        storage1 = JSONStorage(storage_path, collection_name="items")
        storage1.add({"id": "test-1", "name": "Persistent"})

        # Create new instance with same path
        storage2 = JSONStorage(storage_path, collection_name="items")
        items = storage2.get_all()
        assert len(items) == 1
        assert items[0]["name"] == "Persistent"

    def test_handles_empty_filters(self, storage: JSONStorage):
        """Test query with empty filters returns all items."""
        storage.add({"id": "1", "name": "Item 1"})
        storage.add({"id": "2", "name": "Item 2"})
        results = storage.query({})
        assert len(results) == 2


class TestJSONStorageConcurrency:
    """Tests for concurrent access to JSON storage."""

    @pytest.fixture
    def storage(self, tmp_path: Path) -> JSONStorage:
        """Create a storage instance."""
        return JSONStorage(tmp_path / "concurrent.json", collection_name="items")

    def test_multiple_adds(self, storage: JSONStorage):
        """Test multiple sequential adds."""
        for i in range(10):
            storage.add({"id": f"item-{i}", "value": i})
        assert storage.count() == 10

    def test_add_update_delete_sequence(self, storage: JSONStorage):
        """Test a sequence of operations."""
        # Add
        storage.add({"id": "1", "value": "original"})
        assert storage.count() == 1

        # Update
        storage.update("1", {"value": "updated"})
        item = storage.get_by_id("1")
        assert item["value"] == "updated"

        # Delete
        storage.delete("1")
        assert storage.count() == 0

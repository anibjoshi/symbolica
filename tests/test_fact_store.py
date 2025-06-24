"""Tests for FactStore functionality."""

import pytest
from datetime import datetime
from symbolica.core.fact_store import FactStore
from symbolica.core.types import Fact


class TestFactStore:
    """Test cases for FactStore."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.fact_store = FactStore()
    
    def test_add_fact(self):
        """Test adding facts to the store."""
        fact = self.fact_store.add("test_key", "test_value")
        
        assert fact.key == "test_key"
        assert fact.value == "test_value"
        assert len(self.fact_store) == 1
    
    def test_get_fact(self):
        """Test retrieving facts by key."""
        self.fact_store.add("key1", "value1")
        self.fact_store.add("key2", "value2")
        
        facts = self.fact_store.get("key1")
        assert len(facts) == 1
        assert facts[0].value == "value1"
    
    def test_get_latest_fact(self):
        """Test getting the most recent fact."""
        # Add multiple facts with same key
        self.fact_store.add("key1", "old_value")
        fact2 = self.fact_store.add("key1", "new_value")
        
        latest = self.fact_store.get_latest("key1")
        assert latest is not None
        assert latest.value == "new_value"
    
    def test_query_facts(self):
        """Test querying facts with patterns."""
        self.fact_store.add("server_1_status", "running")
        self.fact_store.add("server_2_status", "stopped")
        self.fact_store.add("database_status", "running")
        
        # Test wildcard query
        server_facts = self.fact_store.query("server_*")
        assert len(server_facts) == 2
        
        # Test value query
        running_facts = self.fact_store.query("value:running")
        assert len(running_facts) == 2
    
    def test_remove_facts(self):
        """Test removing facts from the store."""
        self.fact_store.add("key1", "value1")
        self.fact_store.add("key2", "value2")
        
        removed_count = self.fact_store.remove("key1")
        assert removed_count == 1
        assert len(self.fact_store) == 1
        assert "key1" not in self.fact_store
    
    def test_clear_facts(self):
        """Test clearing all facts."""
        self.fact_store.add("key1", "value1")
        self.fact_store.add("key2", "value2")
        
        self.fact_store.clear()
        assert len(self.fact_store) == 0
    
    def test_serialize_deserialize(self):
        """Test serialization and deserialization."""
        self.fact_store.add("key1", "value1", {"tag": "test"})
        self.fact_store.add("key2", 42)
        
        # Serialize
        data = self.fact_store.serialize()
        assert "facts" in data
        assert len(data["facts"]) == 2
        
        # Deserialize into new store
        new_store = FactStore()
        new_store.deserialize(data)
        
        assert len(new_store) == 2
        assert new_store.get("key1")[0].value == "value1"
        assert new_store.get("key2")[0].value == 42
    
    def test_filter_facts(self):
        """Test filtering facts by conditions."""
        self.fact_store.add("server1", "running", {"priority": "high"})
        self.fact_store.add("server2", "stopped", {"priority": "low"})
        self.fact_store.add("server3", "running", {"priority": "medium"})
        
        # Filter by value
        running_servers = self.fact_store.filter_facts([
            {"field": "value", "operator": "==", "value": "running"}
        ])
        assert len(running_servers) == 2
        
        # Filter by metadata
        high_priority = self.fact_store.filter_facts([
            {"field": "metadata.priority", "operator": "==", "value": "high"}
        ])
        assert len(high_priority) == 1
        assert high_priority[0].key == "server1"
    
    def test_fact_metadata(self):
        """Test fact metadata handling."""
        metadata = {"source": "test", "confidence": 0.9}
        fact = self.fact_store.add("test_key", "test_value", metadata)
        
        assert fact.metadata["source"] == "test"
        assert fact.metadata["confidence"] == 0.9
        
        # Test metadata query
        test_facts = self.fact_store.query("meta.source:test")
        assert len(test_facts) == 1
    
    def test_fact_confidence(self):
        """Test fact confidence values."""
        fact1 = self.fact_store.add("key1", "value1")  # Default confidence
        assert fact1.confidence == 1.0
        
        # Test that confidence validation happens in Fact constructor
        with pytest.raises(ValueError):
            Fact(key="invalid", value="test", confidence=1.5)
    
    def test_contains_and_iteration(self):
        """Test __contains__ and __iter__ methods."""
        self.fact_store.add("key1", "value1")
        self.fact_store.add("key2", "value2")
        
        assert "key1" in self.fact_store
        assert "key3" not in self.fact_store
        
        # Test iteration
        facts = list(self.fact_store)
        assert len(facts) == 2
    
    def test_from_json_simple(self):
        """Test creating FactStore from simple JSON."""
        data = {"name": "John", "age": 30, "active": True}
        facts = FactStore.from_json(data)
        
        assert len(facts) == 3
        assert facts.get("name")[0].value == "John"
        assert facts.get("age")[0].value == 30
        assert facts.get("active")[0].value is True
    
    def test_from_json_nested(self):
        """Test creating FactStore from nested JSON."""
        data = {
            "user": {
                "profile": {
                    "name": "Alice",
                    "age": 25
                },
                "settings": {
                    "theme": "dark",
                    "notifications": True
                }
            }
        }
        
        facts = FactStore.from_json(data)
        
        assert facts.get("user.profile.name")[0].value == "Alice"
        assert facts.get("user.profile.age")[0].value == 25
        assert facts.get("user.settings.theme")[0].value == "dark"
        assert facts.get("user.settings.notifications")[0].value is True
    
    def test_load_json_existing_store(self):
        """Test loading JSON into existing fact store."""
        # Add initial facts
        self.fact_store.add("existing", "value")
        
        # Load additional facts from JSON
        new_data = {"new_key": "new_value", "count": 42}
        self.fact_store.load_json(new_data)
        
        assert len(self.fact_store) == 3
        assert self.fact_store.get("existing")[0].value == "value"
        assert self.fact_store.get("new_key")[0].value == "new_value"
        assert self.fact_store.get("count")[0].value == 42 
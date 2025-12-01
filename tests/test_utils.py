import copy
import pickle
import unittest

from dronewq.utils.utils import dotdict


class TestDotdict(unittest.TestCase):
    """Unit tests for the dotdict class."""

    def test_basic_attribute_access(self):
        """Test getting values using dot notation."""
        d = dotdict({"name": "Alice", "age": 30})
        self.assertEqual(d.name, "Alice")
        self.assertEqual(d.age, 30)

    def test_basic_dict_access(self):
        """Test getting values using bracket notation."""
        d = dotdict({"name": "Alice", "age": 30})
        self.assertEqual(d["name"], "Alice")
        self.assertEqual(d["age"], 30)

    def test_set_attribute(self):
        """Test setting values using dot notation."""
        d = dotdict()
        d.name = "Bob"
        d.age = 25
        self.assertEqual(d["name"], "Bob")
        self.assertEqual(d["age"], 25)

    def test_set_item(self):
        """Test setting values using bracket notation."""
        d = dotdict()
        d["name"] = "Charlie"
        d["age"] = 35
        self.assertEqual(d.name, "Charlie")
        self.assertEqual(d.age, 35)

    def test_delete_attribute(self):
        """Test deleting values using dot notation."""
        d = dotdict({"name": "Alice", "age": 30})
        del d.name
        self.assertNotIn("name", d)
        self.assertIn("age", d)

    def test_delete_item(self):
        """Test deleting values using bracket notation."""
        d = dotdict({"name": "Alice", "age": 30})
        del d["age"]
        self.assertNotIn("age", d)
        self.assertIn("name", d)

    def test_attribute_error_on_missing_key(self):
        """Test that accessing a missing attribute raises AttributeError."""
        d = dotdict()
        with self.assertRaises(AttributeError) as context:
            _ = d.missing_key
        self.assertIn("missing_key", str(context.exception))

    def test_key_error_on_missing_item(self):
        """Test that accessing a missing item raises KeyError."""
        d = dotdict()
        with self.assertRaises(KeyError):
            _ = d["missing_key"]

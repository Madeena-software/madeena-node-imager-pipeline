"""Tests for the NodeRegistry — ensures all processors are registered and
return valid node metadata."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.node_registry import NodeRegistry


@pytest.fixture()
def registry():
    return NodeRegistry()


class TestNodeRegistry:
    def test_get_all_nodes_returns_list(self, registry):
        nodes = registry.get_all_nodes()
        assert isinstance(nodes, list)
        assert len(nodes) > 0

    def test_input_and_output_nodes_exist(self, registry):
        nodes = registry.get_all_nodes()
        ids = [n["id"] for n in nodes]
        assert "input" in ids, "Input node must be registered"
        assert "output" in ids, "Output node must be registered"

    def test_every_node_has_required_fields(self, registry):
        required_keys = {
            "id",
            "name",
            "description",
            "type",
            "category",
            "parameters",
            "inputs",
            "outputs",
        }
        for node in registry.get_all_nodes():
            missing = required_keys - set(node.keys())
            assert not missing, f"Node '{node.get('id')}' missing keys: {missing}"

    def test_processor_keys_match_categories(self, registry):
        """Every processor in self.processors should appear in get_all_nodes()."""
        node_ids = {n["id"] for n in registry.get_all_nodes()}
        for key in registry.processors:
            assert key in node_ids, f"Processor '{key}' not found in get_all_nodes()"

    def test_get_processor_returns_instance(self, registry):
        proc = registry.get_processor("resize")
        assert proc is not None
        assert proc.name == "Resize"

    def test_calibration_processors_registered(self, registry):
        calibration_proc = registry.get_processor("camera_calibration")
        apply_proc = registry.get_processor("apply_camera_calibration")
        assert calibration_proc is not None
        assert apply_proc is not None

    def test_get_processor_unknown_returns_none(self, registry):
        assert registry.get_processor("nonexistent_xyz") is None

    def test_no_stale_category_entries(self, registry):
        """The category mapping should not contain keys that don't exist as processors."""
        nodes = registry.get_all_nodes()
        # Processor IDs (excludes input/output which are meta-only)
        processor_ids = {n["id"] for n in nodes if n["type"] == "processor"}
        for node in nodes:
            if node["type"] == "processor":
                assert (
                    node["category"] != "Other"
                ), f"Processor '{node['id']}' has no explicit category (got 'Other')"

    def test_multi_input_nodes_have_input_slots(self, registry):
        for node in registry.get_all_nodes():
            if node.get("multi_input"):
                assert (
                    "input_slots" in node
                ), f"Multi-input node '{node['id']}' missing input_slots"
                assert isinstance(node["input_slots"], list)
                assert len(node["input_slots"]) >= 2

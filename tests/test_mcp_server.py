# -*- coding: utf-8 -*-
"""Tests for the MOFChecker MCP server tools."""
import json
import os

import pytest

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
PADDLEWHEEL_CIF = os.path.join(THIS_DIR, "test_files", "paddlewheel_cn5.cif")
MOF5_CIF = os.path.join(THIS_DIR, "test_files", "mof-5_cellopt.cif")
OVERLAP_CIF = os.path.join(THIS_DIR, "test_files", "ABOVOF_FSR.cif")
MISSING_H_CIF = os.path.join(THIS_DIR, "test_files", "missing_h_on_c.cif")
FLOATING_CIF = os.path.join(THIS_DIR, "test_files", "floating_check.cif")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load(json_str: str) -> dict:
    """Parse JSON returned by a tool and assert no error key."""
    data = json.loads(json_str)
    assert "error" not in data, f"Tool returned an error: {data}"
    return data


# ---------------------------------------------------------------------------
# Tool 1 — list_available_descriptors
# ---------------------------------------------------------------------------


def test_list_available_descriptors():
    from mofchecker.mcp_server import list_available_descriptors

    result = load(list_available_descriptors())
    assert "descriptors" in result
    assert isinstance(result["descriptors"], list)
    assert len(result["descriptors"]) > 0
    # is_porous must NOT be present (handled by zeopp-backend MCP)
    assert "is_porous" not in result["descriptors"]
    # Core descriptors must be present
    for key in ("has_metal", "has_carbon", "has_atomic_overlaps", "formula"):
        assert key in result["descriptors"], f"Expected '{key}' in descriptors"


# ---------------------------------------------------------------------------
# Tool 2 — get_basic_info
# ---------------------------------------------------------------------------


def test_get_basic_info_from_path():
    from mofchecker.mcp_server import get_basic_info

    result = load(get_basic_info(cif_path=PADDLEWHEEL_CIF))
    assert result["formula"] is not None
    assert isinstance(result["density"], float)
    assert isinstance(result["volume"], float)
    assert result["volume"] > 0
    assert isinstance(result["graph_hash"], str)
    assert isinstance(result["symmetry_hash"], str)
    assert isinstance(result["spacegroup_number"], int)


def test_get_basic_info_from_content():
    from mofchecker.mcp_server import get_basic_info

    with open(PADDLEWHEEL_CIF, encoding="utf-8") as f:
        content = f.read()
    result = load(get_basic_info(cif_content=content))
    assert result["formula"] is not None
    assert isinstance(result["density"], float)


def test_get_basic_info_error_no_input():
    from mofchecker.mcp_server import get_basic_info

    data = json.loads(get_basic_info())
    assert "error" in data


def test_get_basic_info_error_bad_path():
    from mofchecker.mcp_server import get_basic_info

    data = json.loads(get_basic_info(cif_path="/nonexistent/path/to/file.cif"))
    assert "error" in data


# ---------------------------------------------------------------------------
# Tool 3 — check_global_structure
# ---------------------------------------------------------------------------


def test_check_global_structure_mof5():
    from mofchecker.mcp_server import check_global_structure

    result = load(check_global_structure(cif_path=MOF5_CIF))
    assert result["has_metal"] is True
    assert result["has_carbon"] is True
    assert result["has_hydrogen"] is True
    assert result["has_3d_connected_graph"] is True


def test_check_global_structure_paddlewheel():
    from mofchecker.mcp_server import check_global_structure

    result = load(check_global_structure(cif_path=PADDLEWHEEL_CIF))
    assert result["has_metal"] is True


# ---------------------------------------------------------------------------
# Tool 4 — check_atomic_overlaps
# ---------------------------------------------------------------------------


def test_check_atomic_overlaps_clean():
    from mofchecker.mcp_server import check_atomic_overlaps

    result = load(check_atomic_overlaps(cif_path=PADDLEWHEEL_CIF))
    assert "has_atomic_overlaps" in result
    assert isinstance(result["overlapping_indices"], list)


def test_check_atomic_overlaps_with_overlaps():
    from mofchecker.mcp_server import check_atomic_overlaps

    result = load(check_atomic_overlaps(cif_path=OVERLAP_CIF))
    assert result["has_atomic_overlaps"] is True
    assert len(result["overlapping_indices"]) > 0


# ---------------------------------------------------------------------------
# Tool 5 — check_coordination
# ---------------------------------------------------------------------------


def test_check_coordination_keys():
    from mofchecker.mcp_server import check_coordination

    result = load(check_coordination(cif_path=PADDLEWHEEL_CIF))
    expected_keys = [
        "has_overcoordinated_c",
        "has_overcoordinated_n",
        "has_overcoordinated_h",
        "has_undercoordinated_c",
        "undercoordinated_c_indices",
        "undercoordinated_c_candidate_positions",
        "has_undercoordinated_n",
        "undercoordinated_n_candidate_positions",
        "has_undercoordinated_rare_earth",
        "has_undercoordinated_alkali_alkaline",
        "has_geometrically_exposed_metal",
    ]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"


def test_check_coordination_missing_h():
    from mofchecker.mcp_server import check_coordination

    result = load(check_coordination(cif_path=MISSING_H_CIF))
    assert result["has_undercoordinated_c"] is True
    assert len(result["undercoordinated_c_indices"]) > 0
    # Candidate positions should be a list of [x, y, z] lists
    positions = result["undercoordinated_c_candidate_positions"]
    assert isinstance(positions, list)
    if positions:
        assert isinstance(positions[0], list)
        assert len(positions[0]) == 3


# ---------------------------------------------------------------------------
# Tool 6 — check_geometry
# ---------------------------------------------------------------------------


def test_check_geometry_keys():
    from mofchecker.mcp_server import check_geometry

    result = load(check_geometry(cif_path=PADDLEWHEEL_CIF))
    assert "has_suspicious_terminal_oxo" in result
    assert "suspicious_terminal_oxo_indices" in result
    assert "has_lone_molecule" in result
    assert "lone_molecule_indices" in result


def test_check_geometry_floating():
    from mofchecker.mcp_server import check_geometry

    result = load(check_geometry(cif_path=FLOATING_CIF))
    assert result["has_lone_molecule"] is True
    assert len(result["lone_molecule_indices"]) > 0


# ---------------------------------------------------------------------------
# Tool 7 — check_charges
# ---------------------------------------------------------------------------


def test_check_charges_keys():
    from mofchecker.mcp_server import check_charges

    result = load(check_charges(cif_path=PADDLEWHEEL_CIF))
    assert "has_high_charges" in result
    # Value should be bool or None
    assert result["has_high_charges"] in (True, False, None)


# ---------------------------------------------------------------------------
# Tool 8 — check_mof_full
# ---------------------------------------------------------------------------


def test_check_mof_full_keys():
    from mofchecker.mcp_server import check_mof_full

    result = load(check_mof_full(cif_path=PADDLEWHEEL_CIF))
    # All standard descriptors must be present (except is_porous)
    from mofchecker import DESCRIPTORS

    for desc in DESCRIPTORS:
        assert desc in result, f"Missing descriptor: {desc}"

    # Extra index fields
    extra_keys = [
        "overlapping_indices",
        "overcoordinated_c_indices",
        "overcoordinated_h_indices",
        "undercoordinated_c_indices",
        "undercoordinated_n_indices",
        "suspicious_terminal_oxo_indices",
        "lone_molecule_indices",
        "spacegroup_symbol",
        "spacegroup_number",
    ]
    for key in extra_keys:
        assert key in result, f"Missing extra key: {key}"


def test_check_mof_full_mof5():
    from mofchecker.mcp_server import check_mof_full

    result = load(check_mof_full(cif_path=MOF5_CIF))
    assert result["has_metal"] is True
    assert result["has_carbon"] is True
    assert result["has_atomic_overlaps"] is False


def test_check_mof_full_error():
    from mofchecker.mcp_server import check_mof_full

    data = json.loads(check_mof_full(cif_path="/no/such/file.cif"))
    assert "error" in data
    assert data["tool"] == "check_mof_full"

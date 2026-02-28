# -*- coding: utf-8 -*-
"""MCP server for MOFChecker.

Exposes MOF structure sanity checks as MCP tools over stdio transport,
designed for integration with FeatherFlow and other MCP-compatible agents.

Usage (stdio, registered via mofchecker-mcp entry point):
    mofchecker-mcp

FeatherFlow config example (~/.featherflow/config.json):
    {
      "tools": {
        "mcpServers": {
          "mofchecker": {
            "command": "mofchecker-mcp",
            "args": [],
            "toolTimeout": 120
          }
        }
      }
    }
"""

from __future__ import annotations

import json
import tempfile
import traceback
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Heavy dependencies (pymatgen, ase …) are loaded lazily on first tool call
# so the MCP initialize handshake can complete before the import finishes.
_MOFChecker = None
_DESCRIPTORS = None


def _lazy_import() -> None:
    """Import mofchecker on first use to avoid blocking MCP startup."""
    global _MOFChecker, _DESCRIPTORS
    if _MOFChecker is None:
        from mofchecker import DESCRIPTORS as _D
        from mofchecker import MOFChecker as _MC
        _MOFChecker = _MC
        _DESCRIPTORS = _D

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "mofchecker",
    instructions=(
        "MOF structure sanity checker. Performs chemical and geometric checks "
        "on Metal-Organic Frameworks from CIF files. Checks include: atomic overlaps, "
        "coordination chemistry, charge analysis, global connectivity, and more."
    ),
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _load_checker(
    cif_path: Optional[str],
    cif_content: Optional[str],
    primitive: bool = False,
):
    """Instantiate MOFChecker from a file path or raw CIF text content."""
    _lazy_import()
    if cif_path:
        return _MOFChecker.from_cif(cif_path, primitive=primitive)
    if cif_content:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".cif", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(cif_content)
            tmp_path = tmp.name
        try:
            checker = _MOFChecker.from_cif(tmp_path, primitive=primitive)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        return checker
    raise ValueError("Either cif_path or cif_content must be provided.")


def _safe_list(iterable) -> list:
    """Convert an iterable of iterables to a JSON-serialisable list of lists."""
    result = []
    for item in iterable:
        try:
            result.append(list(item))
        except TypeError:
            result.append(item)
    return result


def _err(tool: str, exc: Exception) -> str:
    return json.dumps(
        {"error": str(exc), "tool": tool, "detail": traceback.format_exc()},
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Tool 1 — meta
# ---------------------------------------------------------------------------


@mcp.tool()
def list_available_descriptors() -> str:
    """List all descriptor names that MOFChecker can compute.

    Returns a JSON object with key 'descriptors' containing the full list.
    No CIF file is required.
    """
    _lazy_import()
    return json.dumps({"descriptors": _DESCRIPTORS}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 2 — basic info (fast)
# ---------------------------------------------------------------------------


@mcp.tool()
def get_basic_info(
    cif_path: Optional[str] = None,
    cif_content: Optional[str] = None,
    primitive: bool = False,
) -> str:
    """Get basic structural information from a CIF file.

    Returns: name, formula, density (g/cm³), volume (Å³), four graph hashes
    (graph_hash, undecorated_graph_hash, decorated_scaffold_hash,
    undecorated_scaffold_hash), symmetry_hash, spacegroup symbol and number.

    Args:
        cif_path: Absolute path to the CIF file on the local filesystem.
        cif_content: Raw CIF file text content (used when cif_path is unavailable).
        primitive: If True, analyse the primitive cell instead of the as-read cell.
    """
    try:
        mc = _load_checker(cif_path, cif_content, primitive)
        result = {
            "name": mc.name,
            "formula": mc.formula,
            "density": mc.density,
            "volume": mc.volume,
            "graph_hash": mc.graph_hash,
            "undecorated_graph_hash": mc.undecorated_graph_hash,
            "decorated_scaffold_hash": mc.decorated_scaffold_hash,
            "undecorated_scaffold_hash": mc.undecorated_scaffold_hash,
            "symmetry_hash": mc.symmetry_hash,
            "spacegroup_symbol": mc.spacegroup_symbol,
            "spacegroup_number": mc.spacegroup_number,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return _err("get_basic_info", exc)


# ---------------------------------------------------------------------------
# Tool 3 — global structure (fast)
# ---------------------------------------------------------------------------


@mcp.tool()
def check_global_structure(
    cif_path: Optional[str] = None,
    cif_content: Optional[str] = None,
    primitive: bool = False,
) -> str:
    """Check global structural properties of a MOF.

    Checks: metal presence, carbon presence, hydrogen presence,
    and whether the bonding graph is 3-dimensionally connected.

    Args:
        cif_path: Absolute path to the CIF file.
        cif_content: Raw CIF file text content.
        primitive: If True, use the primitive cell.
    """
    try:
        mc = _load_checker(cif_path, cif_content, primitive)
        result = {
            "has_metal": mc.has_metal,
            "has_carbon": mc.has_carbon,
            "has_hydrogen": mc.has_hydrogen,
            "has_3d_connected_graph": mc.has_3d_connected_graph,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return _err("check_global_structure", exc)


# ---------------------------------------------------------------------------
# Tool 4 — atomic overlaps (fast)
# ---------------------------------------------------------------------------


@mcp.tool()
def check_atomic_overlaps(
    cif_path: Optional[str] = None,
    cif_content: Optional[str] = None,
    primitive: bool = False,
) -> str:
    """Check for atomic overlaps (atoms placed unphysically close together).

    Returns whether overlaps exist and the indices of the involved atoms.

    Args:
        cif_path: Absolute path to the CIF file.
        cif_content: Raw CIF file text content.
        primitive: If True, use the primitive cell.
    """
    try:
        mc = _load_checker(cif_path, cif_content, primitive)
        result = {
            "has_atomic_overlaps": mc.has_atomic_overlaps,
            "overlapping_indices": mc.get_overlapping_indices(),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return _err("check_atomic_overlaps", exc)


# ---------------------------------------------------------------------------
# Tool 5 — coordination chemistry (medium speed)
# ---------------------------------------------------------------------------


@mcp.tool()
def check_coordination(
    cif_path: Optional[str] = None,
    cif_content: Optional[str] = None,
    primitive: bool = False,
) -> str:
    """Check coordination chemistry of a MOF structure.

    Detects: over-coordinated C/N/H atoms, under-coordinated C/N atoms
    (with suggested H-addition positions), under-coordinated rare-earth metals,
    under-coordinated alkali/alkaline-earth metals, and geometrically exposed metals.

    Args:
        cif_path: Absolute path to the CIF file.
        cif_content: Raw CIF file text content.
        primitive: If True, use the primitive cell.
    """
    try:
        mc = _load_checker(cif_path, cif_content, primitive)
        result = {
            "has_overcoordinated_c": mc.has_overcoordinated_c,
            "overcoordinated_c_indices": mc.overvalent_c_indices,
            "has_overcoordinated_n": mc.has_overcoordinated_n,
            "has_overcoordinated_h": mc.has_overcoordinated_h,
            "overcoordinated_h_indices": mc.overvalent_h_indices,
            "has_undercoordinated_c": mc.has_undercoordinated_c,
            "undercoordinated_c_indices": mc.undercoordinated_c_indices,
            "undercoordinated_c_candidate_positions": (
                _safe_list(mc.undercoordinated_c_candidate_positions)
                if mc.has_undercoordinated_c
                else []
            ),
            "has_undercoordinated_n": mc.has_undercoordinated_n,
            "undercoordinated_n_indices": mc.undercoordinated_n_indices,
            "undercoordinated_n_candidate_positions": (
                _safe_list(mc.undercoordinated_n_candidate_positions)
                if mc.has_undercoordinated_n
                else []
            ),
            "has_undercoordinated_rare_earth": mc.has_undercoordinated_rare_earth,
            "undercoordinated_rare_earth_indices": mc.undercoordinated_rare_earth_indices,
            "has_undercoordinated_alkali_alkaline": mc.has_undercoordinated_alkali_alkaline,
            "has_geometrically_exposed_metal": mc.has_geometrically_exposed_metal,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return _err("check_coordination", exc)


# ---------------------------------------------------------------------------
# Tool 6 — geometry issues (medium speed)
# ---------------------------------------------------------------------------


@mcp.tool()
def check_geometry(
    cif_path: Optional[str] = None,
    cif_content: Optional[str] = None,
    primitive: bool = False,
) -> str:
    """Check geometric issues in a MOF structure.

    Detects: suspicious terminal oxo groups (likely mis-assigned ligands)
    and floating/lone molecules not connected to the framework.

    Args:
        cif_path: Absolute path to the CIF file.
        cif_content: Raw CIF file text content.
        primitive: If True, use the primitive cell.
    """
    try:
        mc = _load_checker(cif_path, cif_content, primitive)
        result = {
            "has_suspicious_terminal_oxo": mc.has_suspicicious_terminal_oxo,
            "suspicious_terminal_oxo_indices": mc.suspicicious_terminal_oxo_indices,
            "has_lone_molecule": mc.has_lone_molecule,
            "lone_molecule_indices": mc.lone_molecule_indices,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return _err("check_geometry", exc)


# ---------------------------------------------------------------------------
# Tool 7 — charge check (slow: ~5-15 s per structure)
# ---------------------------------------------------------------------------


@mcp.tool()
def check_charges(
    cif_path: Optional[str] = None,
    cif_content: Optional[str] = None,
    primitive: bool = False,
) -> str:
    """Check for unreasonably high EqEq partial charges.

    This is the slowest check (~5-15 s). Returns True if any atom carries
    an unphysically large partial charge, which often indicates a structural error.

    Args:
        cif_path: Absolute path to the CIF file.
        cif_content: Raw CIF file text content.
        primitive: If True, use the primitive cell.
    """
    try:
        mc = _load_checker(cif_path, cif_content, primitive)
        result = {
            "has_high_charges": mc.has_high_charges,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return _err("check_charges", exc)


# ---------------------------------------------------------------------------
# Tool 8 — full check (batch / single-call mode)
# ---------------------------------------------------------------------------


@mcp.tool()
def check_mof_full(
    cif_path: Optional[str] = None,
    cif_content: Optional[str] = None,
    primitive: bool = False,
) -> str:
    """Run the complete MOFChecker suite in a single call.

    Returns all descriptors plus detailed indices. Prefer the individual
    check tools (get_basic_info, check_global_structure, check_atomic_overlaps,
    check_coordination, check_geometry, check_charges) when step-by-step progress
    feedback is desired — each individual call produces a separate tool-hint in
    FeatherFlow's UI.

    Args:
        cif_path: Absolute path to the CIF file.
        cif_content: Raw CIF file text content.
        primitive: If True, use the primitive cell.
    """
    try:
        mc = _load_checker(cif_path, cif_content, primitive)

        # Core descriptors
        result: dict = dict(mc.get_mof_descriptors())

        # Extra index / detail fields not in DESCRIPTORS
        result["overlapping_indices"] = mc.get_overlapping_indices()
        result["overcoordinated_c_indices"] = mc.overvalent_c_indices
        result["overcoordinated_h_indices"] = mc.overvalent_h_indices
        result["undercoordinated_c_indices"] = mc.undercoordinated_c_indices
        result["undercoordinated_c_candidate_positions"] = (
            _safe_list(mc.undercoordinated_c_candidate_positions)
            if mc.has_undercoordinated_c
            else []
        )
        result["undercoordinated_n_indices"] = mc.undercoordinated_n_indices
        result["undercoordinated_n_candidate_positions"] = (
            _safe_list(mc.undercoordinated_n_candidate_positions)
            if mc.has_undercoordinated_n
            else []
        )
        result["undercoordinated_rare_earth_indices"] = mc.undercoordinated_rare_earth_indices
        result["suspicious_terminal_oxo_indices"] = mc.suspicicious_terminal_oxo_indices
        result["lone_molecule_indices"] = mc.lone_molecule_indices
        result["spacegroup_symbol"] = mc.spacegroup_symbol
        result["spacegroup_number"] = mc.spacegroup_number

        # Ensure every value is JSON-serialisable
        serializable = {}
        for k, v in result.items():
            try:
                json.dumps(v)
                serializable[k] = v
            except (TypeError, ValueError):
                serializable[k] = str(v)

        return json.dumps(serializable, ensure_ascii=False)
    except Exception as exc:
        return _err("check_mof_full", exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the MCP server using stdio transport (called by mofchecker-mcp)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

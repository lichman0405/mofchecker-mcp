#!/usr/bin/env python3
"""Quick smoke-test for mofchecker MCP server tools.

Run directly (no MCP client needed — imports tools in-process):
    python test_mcp_server.py

The script calls tools the same way MCP would, and prints pass/fail for each.
"""

import json
import sys
import traceback
from pathlib import Path

TESTS_PASS = []
TESTS_FAIL = []

# Use a small known-good CIF from the test suite
CIF_PATH = str(Path(__file__).parent / "tests" / "test_files" / "mof-5_cellopt.cif")


def check(name: str, result: str, expect_keys: list[str]) -> None:
    try:
        data = json.loads(result)
        if "error" in data:
            print(f"  FAIL  {name}: tool returned error — {data['error']}")
            TESTS_FAIL.append(name)
            return
        missing = [k for k in expect_keys if k not in data]
        if missing:
            print(f"  FAIL  {name}: missing keys {missing}")
            TESTS_FAIL.append(name)
        else:
            print(f"  PASS  {name}")
            TESTS_PASS.append(name)
    except Exception as exc:
        print(f"  FAIL  {name}: {exc}")
        TESTS_FAIL.append(name)


def run():
    # Import the tool functions directly (bypasses MCP transport layer)
    sys.path.insert(0, str(Path(__file__).parent))
    from mofchecker.mcp_server import (
        check_atomic_overlaps,
        check_charges,
        check_coordination,
        check_geometry,
        check_global_structure,
        check_mof_full,
        get_basic_info,
        list_available_descriptors,
    )

    print(f"\nUsing CIF: {CIF_PATH}\n")

    # --- list descriptors (no CIF needed) ---
    print("1) list_available_descriptors")
    try:
        r = list_available_descriptors()
        check("list_available_descriptors", r, ["descriptors"])
    except Exception:
        print(f"  FAIL  list_available_descriptors: {traceback.format_exc()}")
        TESTS_FAIL.append("list_available_descriptors")

    # --- basic info ---
    print("2) get_basic_info")
    try:
        r = get_basic_info(cif_path=CIF_PATH)
        check("get_basic_info", r, ["name", "formula", "density", "graph_hash"])
    except Exception:
        print(f"  FAIL  get_basic_info: {traceback.format_exc()}")
        TESTS_FAIL.append("get_basic_info")

    # --- global structure ---
    print("3) check_global_structure")
    try:
        r = check_global_structure(cif_path=CIF_PATH)
        check("check_global_structure", r, ["has_metal", "has_carbon", "has_3d_connected_graph"])
    except Exception:
        print(f"  FAIL  check_global_structure: {traceback.format_exc()}")
        TESTS_FAIL.append("check_global_structure")

    # --- overlaps ---
    print("4) check_atomic_overlaps")
    try:
        r = check_atomic_overlaps(cif_path=CIF_PATH)
        check("check_atomic_overlaps", r, ["has_atomic_overlaps", "overlapping_indices"])
    except Exception:
        print(f"  FAIL  check_atomic_overlaps: {traceback.format_exc()}")
        TESTS_FAIL.append("check_atomic_overlaps")

    # --- coordination ---
    print("5) check_coordination")
    try:
        r = check_coordination(cif_path=CIF_PATH)
        check("check_coordination", r, ["has_overcoordinated_c", "has_undercoordinated_c"])
    except Exception:
        print(f"  FAIL  check_coordination: {traceback.format_exc()}")
        TESTS_FAIL.append("check_coordination")

    # --- geometry ---
    print("6) check_geometry")
    try:
        r = check_geometry(cif_path=CIF_PATH)
        check("check_geometry", r, ["has_lone_molecule", "has_suspicious_terminal_oxo"])
    except Exception:
        print(f"  FAIL  check_geometry: {traceback.format_exc()}")
        TESTS_FAIL.append("check_geometry")

    # --- charges (slow ~10s) ---
    print("7) check_charges  [slow, ~10 s]")
    try:
        r = check_charges(cif_path=CIF_PATH)
        check("check_charges", r, ["has_high_charges"])
    except Exception:
        print(f"  FAIL  check_charges: {traceback.format_exc()}")
        TESTS_FAIL.append("check_charges")

    # --- full check ---
    print("8) check_mof_full  [slow]")
    try:
        r = check_mof_full(cif_path=CIF_PATH)
        check("check_mof_full", r, ["has_metal", "has_atomic_overlaps", "formula"])
    except Exception:
        print(f"  FAIL  check_mof_full: {traceback.format_exc()}")
        TESTS_FAIL.append("check_mof_full")

    print(f"\n{'='*40}")
    print(f"PASSED: {len(TESTS_PASS)}/{len(TESTS_PASS)+len(TESTS_FAIL)}")
    if TESTS_FAIL:
        print(f"FAILED: {TESTS_FAIL}")
        sys.exit(1)
    else:
        print("All tests passed!")


if __name__ == "__main__":
    run()

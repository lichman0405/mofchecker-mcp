# mofchecker — MCP Edition

> A lean, MCP-enabled repackaging of the outstanding
> [**mofchecker**](https://github.com/lamalab-org/mofchecker) library by
> [Kevin Jablonka](https://github.com/kjappelbaum) and the
> [lamalab-org](https://github.com/lamalab-org) team.

## Standing on the shoulders of giants

The original `mofchecker` is, frankly, one of the most thoughtfully engineered
tools in computational MOF science. In a field where "sanity check" usually means
"did it crash?", Kevin and collaborators built a rigorous, composable framework
that catches everything from overlapping atoms to suspiciously over-charged
fragments — all in a clean, pythonic API that actually makes sense to use. The
graph-hash deduplication alone is worth the price of admission. If you are doing
any serious high-throughput MOF screening, the original library is essential
reading; this fork would not exist without its solid foundation.

**Original repository:** https://github.com/lamalab-org/mofchecker  
**Original paper:** Jablonka et al., *Digital Discovery*, 2023.

---

## What is this fork?

This edition slims the original down to a focused MCP (Model Context Protocol)
server so that AI agents — in particular those built with
[featherflow](https://github.com/lichman0405/featherflow) — can call structure
checks as tools over stdio.

Changes relative to upstream:

| Change | Reason |
|---|---|
| Removed `PorosityCheck` / `is_porous` | Porosity analysis is provided by the separate [`zeopp-backend`](https://github.com/lichman0405/zeopp-backend) MCP service |
| Added `mcp_server.py` with 8 MCP tools | Exposes every check category as an individual callable tool |
| Migrated to `pyproject.toml` (PEP 621) | Modern packaging, single configuration file |
| `python_requires >= 3.9`, dropped `backports.cached-property` | 3.8 is EOL; use `functools.cached_property` from stdlib |
| Replaced `black + isort + flake8` with `ruff` | Single, faster linter/formatter |

Porosity checks are intentionally **not** included here. Point your agent at
`zeopp-backend` (`http://localhost:9877/mcp`) for those.

---

## Installation

> **Important — virtual environment isolation**
> Each MCP server must run in its own virtual environment. The `command` in
> your FeatherFlow config must point to **this project's `.venv/bin/python`**,
> not FeatherFlow's Python or the system Python.

### 0. Install uv (one-time, recommended)

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`uv` manages Python versions automatically — no need to install Python 3.9+ manually.

### 1. Clone and create a dedicated environment

```bash
git clone https://github.com/lichman0405/mofchecker-mcp.git
cd mofchecker-mcp
uv venv .venv --python 3.10        # pyeqeq requires Python <3.11
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\Activate.ps1      # Windows PowerShell
```

### 2. Install

```bash
uv pip install -e .
```

> `pyeqeq` (EQeq charge check) requires Python < 3.11 and pybind11 >= 2.9 (older versions
> have a missing `<cstdint>` include that breaks on GCC 10+).
> Both constraints are handled automatically via `pyproject.toml` — no manual steps needed.

### 3. Verify

```bash
python -m mofchecker.mcp_server --help
```

---

## MCP server

The primary use-case of this fork is running `mofchecker` as an MCP tool server
for AI agents.

### Start the server

```bash
# Activate the project's own venv first
source /path/to/mofchecker/.venv/bin/activate

python -m mofchecker.mcp_server   # stdio transport (for featherflow / Claude Desktop)
```

### Available tools

| Tool | Description |
|---|---|
| `list_available_descriptors` | Returns the full list of descriptor keys |
| `get_basic_info` | Formula, cell volume, density, space group, dimensionality |
| `check_global_structure` | Floating atoms/solvent, graph connectivity |
| `check_atomic_overlaps` | Overlapping atom pairs |
| `check_coordination` | Over/under-coordinated C, N, H and rare-earth/alkaline metals |
| `check_geometry` | Geometrically exposed metals (open metal sites) |
| `check_charges` | EQeq partial-charge sanity (overcharged atoms) |
| `check_mof_full` | Runs all checks and returns the complete descriptor dict |

Every tool accepts either a `cif_path` (absolute path on the server filesystem)
or `cif_content` (raw CIF text) — whichever is more convenient for the caller.

### featherflow integration

Edit `~/.featherflow/config.json`. The `command` must be the **absolute path** to
this project's `.venv/bin/python` — not `mofchecker-mcp` on `$PATH` and not
FeatherFlow's own Python.

```json
{
  "tools": {
    "mcpServers": {
      "mofchecker": {
        "command": "/path/to/mofchecker/.venv/bin/python",
        "args": ["-m", "mofchecker.mcp_server"],
        "toolTimeout": 120
      },
      "zeopp": {
        "url": "http://localhost:9877/mcp",
        "toolTimeout": 120
      }
    }
  },
  "channels": {
    "sendToolHints": true,
    "sendProgress": true
  }
}
```

On Windows replace the path with `C:/path/to/mofchecker/.venv/Scripts/python.exe`.

See [`mcp_config_example.json`](mcp_config_example.json) for a ready-to-use snippet.

---

## Python API

The library is still fully usable as a regular Python package:

```python
from mofchecker import MOFChecker

checker = MOFChecker.from_cif("path/to/structure.cif")

# Individual checks
print(checker.has_atomic_overlaps)     # bool
print(checker.has_oms)                 # bool
print(checker.has_overcoordinated_c)   # bool

# All descriptors at once
descriptors = checker.get_mof_descriptors()
```

---

## Development

```bash
uv pip install -e ".[dev]"
pytest                            # run tests
ruff check mofchecker/ tests/            # lint
ruff format mofchecker/ tests/           # format
```

---

## License

MIT — same as the original project.

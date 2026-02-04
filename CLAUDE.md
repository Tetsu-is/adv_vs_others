# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python research project for analyzing random walk algorithms on graphs. It compares various random walk strategies and measures graph resilience properties.

## Commands

```bash
# Run scripts
uv run python randomwalk.py
uv run python resilience_gain.py <graph.dot> <nodes.txt>

# Install dependencies
uv sync
```

## Architecture

### Random Walk Agents (`randomwalk.py`)

The core module implements a hierarchy of random walk agents on graphs:

- **Base class `SRW`**: Simple Random Walk - tracks path, visit counts, hitting times, and coverage
- **`BiasedRW`**: Transition probability proportional to `degree^alpha`
- **Memory-based agents**: `SARW` (self-avoiding), `BloomRW` (Bloom filter), `kHistory` variants (LRU/FIFO)
- **Backtracking avoidance**: `NBRW` (non-backtracking), `VARW` (vicinity avoidance)
- **Centrality-based**: `EigenvecRW`, `ClosenessRW`, `BetweennessRW`, `EccentricityRW`
- **Special walks**: `MERW` (maximal-entropy), `EmbedRW` (node2vec embeddings), `MaxDegreeRW`, `LZRW` (lazy)

Supported graph types: `random`, `ba`, `barandm`, `ring`, `tree`, `btree`, `lattice`, `voronoi`, `db`, `3-regular`, `4-regular`, `limaini`

### Resilience Analysis (`resilience_gain.py`)

Computes resilience gain using k-core decomposition. Takes a graph (DOT format) and a set of anchor nodes, calculates how core numbers change when anchors are artificially boosted.

### Dependencies

- `graph_tools`: Graph operations and generation (located in `.venv/lib/python3.12/site-packages/graph_tools/__init__.py`)
- `perlcompat`: Perl-style utilities (`die`, `warn`, `getopts`)
- `numpy`: Matrix operations for MERW eigenvalue computation

Note: External packages are installed in `.venv/lib/` directory.
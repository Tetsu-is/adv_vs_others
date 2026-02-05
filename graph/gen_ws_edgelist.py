#!/usr/bin/env python3
"""
Generate a Watts–Strogatz graph with NetworkX and write its edge list to a file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import networkx as nx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Watts–Strogatz graph and write its edge list."
    )
    parser.add_argument("-n", type=int, required=True, help="Number of nodes")
    parser.add_argument(
        "-k",
        type=int,
        required=True,
        help="Each node is connected to k nearest neighbors in ring topology",
    )
    parser.add_argument(
        "-p", type=float, required=True, help="Rewiring probability"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed (optional)"
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        required=True,
        help="Output path for edge list",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    G = nx.watts_strogatz_graph(args.n, args.k, args.p, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    nx.write_edgelist(G, args.out, data=False)


if __name__ == "__main__":
    main()

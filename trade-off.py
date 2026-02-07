#!/usr/bin/env python3
"""
Trade-off analysis: Exploration cost vs Resilience gain
Analyzes how resilience gain changes with random walk steps for a single strategy.
"""

import argparse
import fileinput
import random
import graph_tools
import resilience_gain as rg
import randomwalk
import subprocess
import numpy as np
import scipy.stats as stats
from multiprocessing import Pool, cpu_count


def worker_task(args):
    """
    Worker function for parallel processing.
    Runs n_rw random walk trials for a specific start_point.
    Returns resilience gain and coverage rate at each checkpoint.
    """
    start_idx, start_point, strategy, n_rw, g, budget, checkpoints, seed = args

    # Create a unique seed for this worker to ensure reproducibility
    worker_seed = seed + start_idx * 1000
    rng = random.Random(worker_seed)

    n_checkpoints = len(checkpoints)
    total_vertices = g.nvertices()
    rw_results = {}

    for rw in range(n_rw):
        rw_results[rw] = {}
        # Run the random walk
        agent = randomwalk.create_agent(strategy, graph=g, current=start_point, rng=rng)
        checkpoint_index = 0
        step = 0

        while checkpoint_index < n_checkpoints:
            if step == checkpoints[checkpoint_index]:
                discovered_nodes = agent.get_discovered_graph_with_neighbors()
                edge_list = discovered_nodes.export_edge_list()

                # Calculate coverage rate
                coverage_rate = discovered_nodes.nvertices() / total_vertices

                # Run AdvGreedy to select anchors
                result = subprocess.run(
                    ["./cpp/AdvGreedySelectAnchorStdIn", str(budget)],
                    input=edge_list,
                    capture_output=True,
                    text=True,
                )

                if result.stderr:
                    print(f"Error in external program: {result.stderr}")
                    return None

                anchors = result.stdout.strip().split("\n")
                resilience = rg.resilience_gain(g, anchors)

                # Store both resilience and coverage
                rw_results[rw][checkpoints[checkpoint_index]] = {
                    'resilience': resilience,
                    'coverage': coverage_rate
                }
                checkpoint_index += 1

            agent.advance()
            step += 1

    return (start_idx, rw_results)


def compute_95_ci(data):
    """Compute 95% confidence interval using t-distribution."""
    data = np.array(data)
    n = len(data)
    mean_x = np.mean(data)
    s = np.std(data, ddof=1)  # Unbiased standard deviation
    SE = s / np.sqrt(n)  # Standard error
    t_value = stats.t.ppf(0.975, df=n - 1)  # 95% CI t-value
    CI_lower = mean_x - t_value * SE
    CI_upper = mean_x + t_value * SE

    return mean_x, CI_lower, CI_upper


def generate_checkpoints(max_steps, mode, interval=None, custom_checkpoints=None):
    """
    Generate checkpoints based on mode.

    Args:
        max_steps: Maximum number of steps
        mode: 'interval', 'custom', or 'all'
        interval: Step interval for 'interval' mode
        custom_checkpoints: List of custom checkpoints

    Returns:
        List of checkpoint steps
    """
    if mode == 'all':
        return list(range(max_steps + 1))
    elif mode == 'interval':
        if interval is None:
            interval = 10
        return list(range(0, max_steps + 1, interval))
    elif mode == 'custom':
        if custom_checkpoints is None:
            # Default checkpoints similar to comp_rw_strategies.py
            return [0, 10, 20, 50, 100, 200, 300, 500, 700, 1000]
        return sorted(custom_checkpoints)
    else:
        raise ValueError(f"Invalid mode: {mode}")


def main():
    # ========== Command-line argument parsing ==========
    parser = argparse.ArgumentParser(
        description="Analyze trade-off between exploration cost and resilience gain"
    )
    parser.add_argument(
        "--graph",
        type=str,
        required=True,
        help="Path to graph file (e.g., graph/ba-n-100.edges)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="SRW",
        help="Random walk strategy (default: SRW)",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=10,
        help="Anchor node budget (default: 10)",
    )
    parser.add_argument(
        "--n-start",
        type=int,
        default=30,
        help="Number of different starting points (default: 30)",
    )
    parser.add_argument(
        "--n-rw",
        type=int,
        default=30,
        help="Number of RW trials per starting point (default: 30)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=1000,
        help="Maximum number of RW steps (default: 1000)",
    )
    parser.add_argument(
        "--checkpoint-mode",
        type=str,
        choices=['interval', 'custom', 'all'],
        default='interval',
        help="Checkpoint generation mode: interval, custom, or all (default: interval)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Step interval for checkpoint-mode=interval (default: 10)",
    )
    parser.add_argument(
        "--checkpoints",
        type=str,
        default=None,
        help="Comma-separated custom checkpoint steps (e.g., '0,10,50,100,500,1000')",
    )
    parser.add_argument(
        "--n-workers",
        type=int,
        default=None,
        help="Number of parallel workers (default: CPU count)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    # ========== Configuration ==========
    graph_path = args.graph
    strategy = args.strategy
    budget = args.budget
    n_start = args.n_start
    n_rw = args.n_rw
    max_steps = args.max_steps
    n_workers = args.n_workers if args.n_workers else cpu_count()
    seed = args.seed

    # Parse custom checkpoints if provided
    custom_checkpoints = None
    if args.checkpoints:
        custom_checkpoints = [int(x.strip()) for x in args.checkpoints.split(',')]

    # Generate checkpoints
    # checkpoints = generate_checkpoints(
    #     max_steps,
    #     args.checkpoint_mode,
    #     args.interval,
    #     custom_checkpoints
    # )
    checkpoints = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]

    print("🚀 Starting trade-off analysis")
    print(f"   Graph: {graph_path}")
    print(f"   Strategy: {strategy}")
    print(f"   Budget: {budget}")
    print(f"   Starting points: {n_start}")
    print(f"   RW trials per start: {n_rw}")
    print(f"   Max steps: {max_steps}")
    print(f"   Checkpoints: {len(checkpoints)} points ({checkpoints[:5]}...{checkpoints[-3:]})")
    print(f"   Workers: {n_workers}")
    print()

    # ========== Load graph ==========
    lines = []
    for line in fileinput.input(files=(graph_path,)):
        line = line.rstrip()
        lines.append(line)

    g = graph_tools.Graph(directed=False)
    g.import_edge_list(lines)

    # Check connectivity
    if not g.is_connected():
        print("❌ Error: The graph is not connected. Please provide a connected graph.")
        return

    print(f"✅ Graph loaded: {g.nvertices()} vertices, {g.nedges()} edges")

    # ========== Prepare parallel tasks ==========
    rng = random.Random(seed)
    start_points = [rng.choice(list(g.vertices())) for _ in range(n_start)]

    tasks = []
    for start_idx in range(n_start):
        tasks.append(
            (
                start_idx,
                start_points[start_idx],
                strategy,
                n_rw,
                g,
                budget,
                checkpoints,
                seed,
            )
        )

    print(f"🔥 Running {len(tasks)} parallel tasks...")

    # ========== Parallel execution ==========
    with Pool(processes=n_workers) as pool:
        task_results = pool.map(worker_task, tasks)

    # ========== Reconstruct results ==========
    results = {}
    for task_result in task_results:
        if task_result is None:
            print("❌ Error: One or more tasks failed")
            return
        start_idx, rw_results = task_result
        results[start_idx] = rw_results

    # ========== Calculate statistics and output ==========
    # First, collect all statistics
    resilience_stats = []
    coverage_stats = []

    for checkpoint in checkpoints:
        # Step 1: Average across RW trials for each starting point
        start_avg_resilience = []
        start_avg_coverage = []

        for start_idx in range(n_start):
            rw_resilience_values = []
            rw_coverage_values = []

            for rw in range(n_rw):
                if checkpoint in results[start_idx][rw]:
                    rw_resilience_values.append(results[start_idx][rw][checkpoint]['resilience'])
                    rw_coverage_values.append(results[start_idx][rw][checkpoint]['coverage'])

            if rw_resilience_values:
                start_avg_resilience.append(np.mean(rw_resilience_values))
                start_avg_coverage.append(np.mean(rw_coverage_values))

        # Step 2: Calculate mean and 95% CI across starting points
        if start_avg_resilience:
            mean_res, ci_res_lower, ci_res_upper = compute_95_ci(start_avg_resilience)
            mean_cov, ci_cov_lower, ci_cov_upper = compute_95_ci(start_avg_coverage)

            res_ci_width = ci_res_upper - ci_res_lower
            cov_ci_width = ci_cov_upper - ci_cov_lower

            resilience_stats.append((checkpoint, mean_res, res_ci_width))
            coverage_stats.append((checkpoint, mean_cov, cov_ci_width))
        else:
            resilience_stats.append((checkpoint, None, None))
            coverage_stats.append((checkpoint, None, None))

    # ========== Output Resilience Gain Results ==========
    print(f"\n{'=' * 70}")
    print(f"RESILIENCE GAIN: {strategy} on {graph_path}")
    print('=' * 70)
    print("# Step Mean_Resilience CI_Width")
    print('=' * 70 + '\n')

    for checkpoint, mean_res, ci_width in resilience_stats:
        if mean_res is not None:
            print(f"{checkpoint:4d} {mean_res:.6f} {ci_width:.6f}")
        else:
            print(f"{checkpoint:4d} No data")

    # ========== Output Coverage Results ==========
    print(f"\n{'=' * 70}")
    print(f"COVERAGE: {strategy} on {graph_path}")
    print('=' * 70)
    print("# Step Mean_Coverage CI_Width")
    print('=' * 70 + '\n')

    for checkpoint, mean_cov, ci_width in coverage_stats:
        if mean_cov is not None:
            print(f"{checkpoint:4d} {mean_cov:.6f} {ci_width:.6f}")
        else:
            print(f"{checkpoint:4d} No data")

    print(f"\n{'=' * 70}")
    print("✨ Analysis complete!")
    print('=' * 70)


if __name__ == "__main__":
    main()

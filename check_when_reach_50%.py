import random
import randomwalk
import graph_tools
import fileinput
import argparse
from multiprocessing import Pool, cpu_count


def run_single_walk(args):
    """Run a single random walk experiment and return checkpoint steps."""
    agent_type, graph_lines, start_node, seed, checkpoints = args

    # Reconstruct graph for this process
    g = graph_tools.Graph(directed=False)
    g.import_edge_list(graph_lines)

    rng = random.Random(seed)
    agent = randomwalk.create_agent(agent_type, graph=g, current=start_node, rng=rng)

    checkpoint_steps = {}

    coverage = 0
    step = 0
    checkpoint_index = 0

    while checkpoint_index < len(checkpoints):
        discoverd_nodes = agent.get_discovered_graph_with_neighbors()
        coverage = discoverd_nodes.nvertices() / g.nvertices()
        if coverage >= checkpoints[checkpoint_index]:
            current_checkpoint = checkpoints[checkpoint_index]
            checkpoint_steps[current_checkpoint] = step
            checkpoint_index += 1
        agent.advance()
        step += 1

    return agent_type, checkpoint_steps


def main():
    parser = argparse.ArgumentParser(
        description="Check When Random Walk Reaches Coverage Checkpoints"
    )
    parser.add_argument(
        "--graph",
        type=str,
        default="graph/ba-n-1000.edges",
        help="Path to the graph file (default: graph/ba-n-1000.edges)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of runs per agent type (default: 10)",
    )
    parser.add_argument(
        "--checkpoints",
        type=str,
        default="0.1,0.2,0.3",
        help="Comma-separated coverage checkpoints to track (default: 0.1,0.2,0.3,0.4,0.5)",
    )
    args = parser.parse_args()

    # Parse checkpoints from comma-separated string
    checkpoints = [float(cp.strip()) for cp in args.checkpoints.split(",")]
    checkpoints.sort()  # Ensure they're in ascending order

    # Load graph
    file = args.graph
    g = graph_tools.Graph(directed=False)
    lines = []
    for line in fileinput.input(files=(file,)):
        line = line.rstrip()
        lines.append(line)

    g.import_edge_list(lines)

    # Pre-generate starting nodes for consistency across agent types
    seed = 1
    rng = random.Random(seed)
    start_nodes = [rng.choice(list(g.vertices())) for _ in range(args.runs)]

    # Agent types to compare
    agent_types = ["SRW", "NBRW", "VARW", "SARW"]

    print(f"🚀 Running {args.runs} experiments for each agent type in parallel...")
    print(f"📊 Graph: {file} ({g.nvertices()} vertices)")
    print(f"🔄 Agent types: {', '.join(agent_types)}")
    print(f"📍 Checkpoints: {', '.join([f'{int(cp*100)}%' for cp in checkpoints])}\n")

    # Create all tasks (agent_type, graph_lines, start_node, seed, checkpoints) combinations
    tasks = []
    for agent_type in agent_types:
        for i, start_node in enumerate(start_nodes):
            # Use different seed for each run
            task_seed = seed + i
            tasks.append((agent_type, lines, start_node, task_seed, checkpoints))

    # Run all tasks in a single flat pool (no nesting!)
    with Pool(processes=cpu_count()) as pool:
        all_results = pool.map(run_single_walk, tasks)

    # Aggregate results by agent type
    results_dict = {
        agent_type: {cp: [] for cp in checkpoints} for agent_type in agent_types
    }

    for agent_type, checkpoint_steps in all_results:
        for cp, steps in checkpoint_steps.items():
            results_dict[agent_type][cp].append(steps)

    # Display results
    print("=" * 80)
    print("📈 AVERAGE STEPS TO REACH COVERAGE")
    print("=" * 80)

    # Print header
    print(f"{'Coverage':<12}", end="")
    for agent_type in agent_types:
        print(f"{agent_type:<15}", end="")
    print()
    print("-" * 80)

    # Print results for each checkpoint
    for cp in checkpoints:
        print(f"{int(cp * 100)}%{'':<9}", end="")
        for agent_type in agent_types:
            checkpoint_steps = results_dict[agent_type][cp]
            avg_steps = sum(checkpoint_steps) / len(checkpoint_steps)
            print(f"{avg_steps:<15.2f}", end="")
        print()

    print("=" * 80)

    # Print comparison summary for the highest checkpoint
    highest_cp = checkpoints[-1]
    print(f"\n🏆 COMPARISON AT {int(highest_cp * 100)}% COVERAGE")
    print("-" * 40)
    results_highest = []
    for agent_type in agent_types:
        if results_dict[agent_type][highest_cp]:  # Check if data exists
            avg_highest = sum(results_dict[agent_type][highest_cp]) / len(results_dict[agent_type][highest_cp])
            results_highest.append((agent_type, avg_highest))

    results_highest.sort(key=lambda x: x[1])
    for rank, (agent_type, avg_steps) in enumerate(results_highest, 1):
        emoji = (
            "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "📊"
        )
        print(f"{emoji} {rank}. {agent_type}: {avg_steps:.2f} steps")


if __name__ == "__main__":
    main()

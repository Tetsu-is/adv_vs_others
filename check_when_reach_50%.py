import random
import randomwalk
import graph_tools
import fileinput
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Check When Random Walk Reaches 50% Coverage"
    )
    parser.add_argument(
        "--graph",
        type=str,
        default="graph/ba-n-1000.edges",
        help="Path to the graph file (default: graph/ba-n-1000.edges)",
    )
    args = parser.parse_args()
    file = args.graph
    g = graph_tools.Graph(directed=False)
    lines = []
    for line in fileinput.input(files=(file,)):
        line = line.rstrip()
        lines.append(line)

    g.import_edge_list(lines)
    # print(g.nvertices())

    seed = 1
    rng = random.Random(seed)

    checkpoints = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.9]  # Coverage checkpoints
    # Store step counts for each checkpoint across all runs
    checkpoint_steps = {cp: [] for cp in checkpoints}

    for i in range(10):
        start = rng.choice(list(g.vertices()))
        agent = randomwalk.create_agent("SRW", graph=g, current=start, rng=rng)

        # 先にいくらくらいで被覆50%にいくのか知っときたい感ある
        coverage = 0
        step = 0
        checkpoint_index = 0

        while checkpoint_index < len(checkpoints):
            discoverd_nodes = agent.get_discovered_graph_with_neighbors()
            coverage = discoverd_nodes.nvertices() / g.nvertices()
            if coverage >= checkpoints[checkpoint_index]:
                current_checkpoint = checkpoints[checkpoint_index]
                checkpoint_steps[current_checkpoint].append(step)
                checkpoint_index += 1
            agent.advance()
            step += 1

    # Calculate and display averages
    print("\n=== Average Steps to Reach Coverage ===")
    for cp in checkpoints:
        avg_steps = sum(checkpoint_steps[cp]) / len(checkpoint_steps[cp])
        print(f"{int(cp * 100)}% coverage: {avg_steps:.2f} steps (average)")

if __name__ == "__main__":
    main()

# uv run main.py
# Run 1:
# 10% coverage reached at step 19
# 20% coverage reached at step 39
# 30% coverage reached at step 53
# 40% coverage reached at step 54
# 50% coverage reached at step 66
# Run 2:
# 10% coverage reached at step 1
# 20% coverage reached at step 2
# 30% coverage reached at step 8
# 40% coverage reached at step 24
# 50% coverage reached at step 40
# Run 3:
# 10% coverage reached at step 9
# 20% coverage reached at step 19
# 30% coverage reached at step 20
# 40% coverage reached at step 42
# 50% coverage reached at step 83
# Run 4:
# 10% coverage reached at step 6
# 20% coverage reached at step 7
# 30% coverage reached at step 20
# 40% coverage reached at step 54
# 50% coverage reached at step 93
# Run 5:
# 10% coverage reached at step 11
# 20% coverage reached at step 31
# 30% coverage reached at step 39
# 40% coverage reached at step 52
# 50% coverage reached at step 53
# Run 6:
# 10% coverage reached at step 10
# 20% coverage reached at step 29
# 30% coverage reached at step 36
# 40% coverage reached at step 37
# 50% coverage reached at step 63
# Run 7:
# 10% coverage reached at step 22
# 20% coverage reached at step 23
# 30% coverage reached at step 26
# 40% coverage reached at step 34
# 50% coverage reached at step 55
# Run 8:
# 10% coverage reached at step 4
# 20% coverage reached at step 19
# 30% coverage reached at step 24
# 40% coverage reached at step 27
# 50% coverage reached at step 56
# Run 9:
# 10% coverage reached at step 14
# 20% coverage reached at step 24
# 30% coverage reached at step 39
# 40% coverage reached at step 53
# 50% coverage reached at step 54
# Run 10:
# 10% coverage reached at step 7
# 20% coverage reached at step 8
# 30% coverage reached at step 14
# 40% coverage reached at step 52
# 50% coverage reached at step 80
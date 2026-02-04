import random
import randomwalk
import graph_tools
import fileinput


def main():
    file = "graph/ba-n-7.edges"
    g = graph_tools.Graph(directed=False)
    lines = []
    for line in fileinput.input(files=(file,)):
        line = line.rstrip()
        lines.append(line)

    g.import_edge_list(lines)
    print(f"Graph loaded: {g.nvertices()} vertices, {g.nedges()} edges")
    print(f"Vertices: {list(g.vertices())}")

    seed = 42
    rng = random.Random(seed)
    start = "1"
    print(f"\nStarting from vertex: {start}")
    print(f"Neighbors of 1: {list(g.neighbors('1'))}")

    agent = randomwalk.create_agent("SRW", graph=g, current=start, rng=rng)

    # 固定の移動先
    moves = ["2", "4"]

    def print_status(label):
        print(f"\n--- {label} ---")
        print(f"Current position: {agent.current}")
        print(f"Visited nodes: {[v for v in g.vertices() if agent.nvisits[v] > 0]}")

        discovered = agent.get_discovered_graph_with_neighbors()
        print(f"Discovered graph (with neighbors):")
        print(f"  Vertices ({discovered.nvertices()}): {list(discovered.vertices())}")
        print(f"  Edges ({discovered.nedges()}): {list(discovered.edges())}")

    # 初期状態
    print_status("Initial (at node 1)")

    # 2歩進む
    for i, dest in enumerate(moves):
        agent.move_to(dest)
        print_status(f"After move {i+1}: 1 -> {dest}")


if __name__ == "__main__":
    main()

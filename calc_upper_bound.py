# このプログラムは与えられたグラフに対してcpp/AdvGreedySelectAnchorStdInを用いてアンカーを決定して
# resilience_gainモジュールのresilience_gain関数を用いてResilience Gainを計算して出力するものです。

import sys
import fileinput
import subprocess
import graph_tools
import resilience_gain as rg


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run calc_upper_bound.py <graph.edges> [budget]", file=sys.stderr)
        sys.exit(1)

    graph_file = sys.argv[1]
    budget = int(sys.argv[2]) if len(sys.argv) >= 3 else 5

    # グラフ読み込み
    g = graph_tools.Graph(directed=False)
    lines = []
    for line in fileinput.input(files=(graph_file,)):
        line = line.rstrip()
        lines.append(line)
    g.import_edge_list(lines)

    # エッジリストをエクスポート
    edge_list = g.export_edge_list()

    # AdvGreedyでアンカーを決定
    result = subprocess.run(
        ["./cpp/AdvGreedySelectAnchorStdIn", str(budget)],
        input=edge_list,
        capture_output=True,
        text=True
    )

    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"AdvGreedySelectAnchorStdIn failed with return code {result.returncode}", file=sys.stderr)
        sys.exit(1)

    anchors = result.stdout.strip().split('\n')

    # Resilience Gainを計算
    gain = rg.resilience_gain(g, anchors)

    # 結果を出力
    print(f"Graph: {graph_file}")
    print(f"Nodes: {g.nvertices()}")
    print(f"Edges: {g.nedges()}")
    print(f"Avg Degree: {2 * g.nedges() / g.nvertices():.2f}")
    print(f"is Connected: {g.is_connected()}")
    print(f"Budget: {budget}")
    print(f"Anchors: {anchors}")
    print(f"Resilience Gain: {gain}")


if __name__ == "__main__":
    main()

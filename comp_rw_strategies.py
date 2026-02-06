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

def main():
    # ========== コマンドライン引数のパース ==========
    parser = argparse.ArgumentParser(
        description="Compare Randomwalk Strategies on Graphs"
    )
    parser.add_argument(
        "--graph",
        type=str,
        default="graph/ba-n-1000.edges",
        help="グラフファイルのパス (default: graph/ba-n-1000.edges)",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=10,
        help="アンカーノードのバジェット (default: 10)",
    )
    parser.add_argument(
        "--n-start", type=int, default=100, help="開始点選択の試行回数 (default: 100)"
    )
    parser.add_argument(
        "--n-rw", type=int, default=100, help="各開始点からのRW試行回数 (default: 100)"
    )
    args = parser.parse_args()

    graph_path = args.graph
    budget = args.budget
    n_start = args.n_start
    n_rw = args.n_rw

    # ========== グラフ読み込み ==========
    lines = []
    for line in fileinput.input(files=(graph_path,)):
        line = line.rstrip()
        lines.append(line)

    g = graph_tools.Graph(directed=False)
    g.import_edge_list(lines)

    # 連結性の確認。非連結の場合は最大連結成分を用いる
    if not g.is_connected():
        print("Error: The graph is not connected. Please provide a connected graph.")
        return

    # ========== (randomwalk startegies) x (n-start) x (n-rw) のパターン分シミュレーション ==========
    strategies = ["SRW", "NBRW", "VARW", "SARW"]
    checkpoints = [10, 20, 30, 40, 50]  # 探索ステップのチェックポイント
    n_checkpoints = len(checkpoints)
    seed = 1
    rng = random.Random(seed)

    results = {}

    for strategy in strategies:
        results[strategy] = {}
        for start in range(n_start):
            results[strategy][start] = {}
            start_point = rng.choice(list(g.vertices()))
            for rw in range(n_rw):
                results[strategy][start][rw] = {}
                # ランダムウォークの実行
                agent = randomwalk.create_agent(
                    strategy, graph=g, current=start_point, rng=rng
                )
                checkpoint_index = 0
                step = 0
                while checkpoint_index < n_checkpoints:
                    if step == checkpoints[checkpoint_index]:
                        discovered_nodes = agent.get_discovered_graph_with_neighbors()
                        edge_list = discovered_nodes.export_edge_list()
                        result = subprocess.run(
                            ["./cpp/AdvGreedySelectAnchorStdIn", str(budget)],
                            input=edge_list,
                            capture_output=True,
                            text=True,
                        )
                        if result.stderr:
                            print(f"Error in external program: {result.stderr}")
                            return
                        anchors = result.stdout.strip().split("\n")
                        resilience = rg.resilience_gain(g, anchors)
                        results[strategy][start][rw][checkpoints[checkpoint_index]] = resilience
                        checkpoint_index += 1
                    agent.advance()
                    step += 1

    # ========== 結果表示 ==========
    print(f"Graph Path: {graph_path}")
    print(f"Budget: {budget}")
    print(f"Number of Start Points: {n_start}")
    print(f"Number of Random Walks per Start Point: {n_rw}")
    print()

    for strategy in strategies:
        print(f"# {strategy}")
        for checkpoint in checkpoints:
            # Step 1: 各開始点について、RW試行回数分の平均を取る
            start_averages = []
            for start in range(n_start):
                rw_values = []
                for rw in range(n_rw):
                    rw_values.append(results[strategy][start][rw][checkpoint])
                rw_avg = np.mean(rw_values)
                start_averages.append(rw_avg)

            # Step 2: 開始点分の平均と信頼区間を計算
            mean_resilience, ci_lower, ci_upper = compute_95_ci(start_averages)

            print(f"  Checkpoint {checkpoint}: Mean={mean_resilience:.4f}, 95% CI=[{ci_upper - ci_lower:.4f}]")
        print()

def compute_95_ci(data):
    data = np.array(data)
    n = len(data)
    mean_x = np.mean(data)
    s = np.std(data, ddof=1)  # 不偏標準偏差
    SE = s / np.sqrt(n)  # 標準誤差
    t_value = stats.t.ppf(0.975, df=n - 1)  # 95%信頼区間の t 値
    CI_lower = mean_x - t_value * SE
    CI_upper = mean_x + t_value * SE

    return mean_x, CI_lower, CI_upper

if __name__ == "__main__":
    main()

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
    Runs n_rw random walk trials for a specific (strategy, start_point) combination.
    """
    strategy, start_idx, start_point, n_rw, g, budget, checkpoints, seed = args

    # Create a unique seed for this worker to ensure reproducibility
    worker_seed = seed + start_idx * 1000 + hash(strategy) % 1000
    rng = random.Random(worker_seed)

    n_checkpoints = len(checkpoints)
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
                rw_results[rw][checkpoints[checkpoint_index]] = resilience
                checkpoint_index += 1
            agent.advance()
            step += 1

    return (strategy, start_idx, rw_results)


def main():
    # ========== コマンドライン引数のパース ==========
    parser = argparse.ArgumentParser(
        description="Compare Randomwalk Strategies on Graphs (Parallel Version)"
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
    parser.add_argument(
        "--n-workers",
        type=int,
        default=None,
        help="並列処理のワーカー数 (default: CPUコア数)",
    )
    args = parser.parse_args()

    graph_path = args.graph
    budget = args.budget
    n_start = args.n_start
    n_rw = args.n_rw
    n_workers = args.n_workers if args.n_workers else cpu_count()

    print(f"🚀 Using {n_workers} parallel workers")

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

    # ========== 並列処理のタスク準備 ==========
    strategies = ["SRW", "NBRW", "VARW", "SARW"]
    checkpoints = [
        100,
        200,
        300,
        400,
        500,
        600,
        700,
        800,
        900,
        1000,
    ]  # 探索ステップのチェックポイント
    seed = 1
    rng = random.Random(seed)

    # Generate start points for reproducibility
    start_points = [rng.choice(list(g.vertices())) for _ in range(n_start)]

    # Create all tasks (strategy, start_point) combinations
    tasks = []
    for strategy in strategies:
        for start_idx in range(n_start):
            tasks.append(
                (
                    strategy,
                    start_idx,
                    start_points[start_idx],
                    n_rw,
                    g,
                    budget,
                    checkpoints,
                    seed,
                )
            )

    print(f"🔥 Running {len(tasks)} parallel tasks...")

    # ========== 並列実行 ==========
    with Pool(processes=n_workers) as pool:
        task_results = pool.map(worker_task, tasks)

    # ========== 結果を元の構造に再構築 ==========
    results = {}
    for task_result in task_results:
        if task_result is None:
            print("Error: One or more tasks failed")
            return
        strategy, start_idx, rw_results = task_result
        if strategy not in results:
            results[strategy] = {}
        results[strategy][start_idx] = rw_results

    # ========== 結果表示 ==========
    print(f"\n{'=' * 60}")
    print(f"Graph Path: {graph_path}")
    print(f"Budget: {budget}")
    print(f"Number of Start Points: {n_start}")
    print(f"Number of Random Walks per Start Point: {n_rw}")
    print(f"{'=' * 60}\n")

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

            print(f"{checkpoint} {mean_resilience:.4f} {ci_upper - ci_lower:.4f}")
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

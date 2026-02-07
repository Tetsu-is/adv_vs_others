## ランダムウォークで得た部分グラフに対するアンカー決定手法としてAdvGreedy, DegreeCentrality, RandomSelect, DegreeCentralityReverseを比較するスクリプト

import os
import random
import randomwalk
import graph_tools
import fileinput
import subprocess
import scipy.stats as stats
import numpy as np
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor
import time
import argparse
import resilience_gain as rg

# パラメータ（main()でargparseから設定される）
GRAPH_PATH = None
BUDGET = None
N_START_ATTEMPTS = None
N_RW_ATTEMPTS = None

# グローバル変数（ワーカープロセスで共有）
_graph_lines = None
_checkpoints = None
_n_checkpoints = None
_g = None  # キャッシュされたグラフインスタンス
_budget = None
_n_rw_attempts = None


def init_worker(graph_lines, checkpoints, budget, n_rw_attempts):
    """ワーカープロセスの初期化"""
    global _graph_lines, _checkpoints, _n_checkpoints, _g, _budget, _n_rw_attempts
    _graph_lines = graph_lines
    _checkpoints = checkpoints
    _n_checkpoints = len(checkpoints)
    _budget = budget
    _n_rw_attempts = n_rw_attempts
    # ワーカープロセスごとに1回だけグラフを構築
    _g = graph_tools.Graph(directed=False)
    _g.import_edge_list(_graph_lines)


def run_start_node(args):
    """1つの開始ノードに対するRW試行を実行"""
    _, worker_seed = args

    # キャッシュされたグラフを使用（読み取り専用なので安全）
    g = _g

    rng = random.Random(worker_seed)
    start = rng.choice(list(g.vertices()))

    # startごとの結果
    results_AG = {i: [] for i in range(_n_checkpoints)}
    results_DC = {i: [] for i in range(_n_checkpoints)}
    results_RS = {i: [] for i in range(_n_checkpoints)}
    results_DCR = {i: [] for i in range(_n_checkpoints)}

    for _ in range(_n_rw_attempts):
        agent = randomwalk.create_agent("SRW", graph=g, current=start, rng=rng)
        checkpoint_index = 0

        while checkpoint_index < len(_checkpoints):
            # O(1)でcoverageを計算
            coverage = agent.coverage_with_neighbors()
            if coverage >= _checkpoints[checkpoint_index]:
                # checkpointに到達したときだけグラフを構築
                discovered_graph = agent.get_discovered_graph_with_neighbors()
                ## アンカー決定
                edge_list = discovered_graph.export_edge_list()
                budget = _budget
                discovered_nodes = discovered_graph.vertices()

                # 3手法を並列実行
                def calc_adv():
                    result = subprocess.run(
                        ["./cpp/AdvGreedySelectAnchorStdIn", str(budget)],
                        input=edge_list,
                        capture_output=True,
                        text=True,
                    )
                    if result.stderr:
                        print(result.stderr)
                    anchors = result.stdout.strip().split("\n")
                    return rg.resilience_gain(g, anchors)

                def calc_dc():
                    anchors = sorted(
                        discovered_nodes,
                        key=lambda v: discovered_graph.degree(v),
                        reverse=True,
                    )[:budget]
                    return rg.resilience_gain(g, anchors)

                def calc_dcr():
                    anchors = sorted(
                        discovered_nodes,
                        key=lambda v: discovered_graph.degree(v),
                    )[:budget]
                    return rg.resilience_gain(g, anchors)

                def calc_rs():
                    anchors = rng.sample(list(discovered_nodes), k=budget)
                    return rg.resilience_gain(g, anchors)

                with ThreadPoolExecutor(max_workers=3) as executor:
                    future_adv = executor.submit(calc_adv)
                    future_dc = executor.submit(calc_dc)
                    future_rs = executor.submit(calc_rs)
                    future_dcr = executor.submit(calc_dcr)

                    rg_by_adv = future_adv.result()
                    rg_by_DC = future_dc.result()
                    rg_by_RS = future_rs.result()
                    rg_by_DCR = future_dcr.result()

                # 集計用にデータを保存
                results_AG[checkpoint_index].append(rg_by_adv)
                results_DC[checkpoint_index].append(rg_by_DC)
                results_RS[checkpoint_index].append(rg_by_RS)
                results_DCR[checkpoint_index].append(rg_by_DCR)

                checkpoint_index += 1

            agent.advance()

    return results_AG, results_DC, results_RS, results_DCR


# ==== main ====
def main():
    global GRAPH_PATH, BUDGET, N_START_ATTEMPTS, N_RW_ATTEMPTS

    parser = argparse.ArgumentParser(description="Random walk resilience gain analysis")
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

    GRAPH_PATH = args.graph
    BUDGET = args.budget
    N_START_ATTEMPTS = args.n_start
    N_RW_ATTEMPTS = args.n_rw

    start_time = time.perf_counter()
    os.makedirs("tmp", exist_ok=True)
    file = GRAPH_PATH

    # RGUpperBound = calc_upper_rg_bound()

    # グラフデータを読み込み
    lines = []
    for line in fileinput.input(files=(file,)):
        line = line.rstrip()
        lines.append(line)

    # メインプロセス用のグラフ（集計で使用）
    g = graph_tools.Graph(directed=False)
    g.import_edge_list(lines)

    # 連結性の確認。非連結の場合は最大連結成分を用いる
    if not g.is_connected():
        print("===Graph is not connected. Using the largest connected component.===")
        gcc = g.maximal_component()
        nodes_to_remove = set(g.vertices()) - gcc
        for v in nodes_to_remove:
            g.delete_vertex(v)
        print(f"GCC size: {g.nvertices()} nodes, {g.nedges()} edges.")

    base_seed = 1
    checkpoints = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # Coverage checkpoints
    n_checkpoints = len(checkpoints)

    # 各ワーカーに異なるシードを割り当て
    n_starts = N_START_ATTEMPTS
    worker_args = [(i, base_seed + i * 1000) for i in range(n_starts)]

    # 並列実行
    n_workers = min(cpu_count(), n_starts)
    print(f"Using {n_workers} workers for {n_starts} start nodes")

    with Pool(
        processes=n_workers,  # ワーカープロセス数の指定
        initializer=init_worker,  # ワーカープロセスの初期化関数
        initargs=(lines, checkpoints, BUDGET, N_RW_ATTEMPTS),
    ) as pool:
        results = pool.map(run_start_node, worker_args)

    # 結果を展開
    results_AG_by_start = [r[0] for r in results]
    results_DC_by_start = [r[1] for r in results]
    results_RS_by_start = [r[2] for r in results]
    results_DCR_by_start = [r[3] for r in results]

    # 結果を集計する（RW試行平均→start平均）
    def mean_or_none(values):
        if not values:
            print("No values to compute mean.")
            return None
        return sum(values) / len(values)

    def mean_ci_over_starts(results_by_start):
        """各開始ノードでのRW試行平均を計算し、それらの平均と95%信頼区間を返す"""
        # Step 1: 各開始ノードでのRW試行の平均を計算
        per_start_means = []
        for start_results in results_by_start:
            per_start_means.append(
                {i: mean_or_none(start_results[i]) for i in range(n_checkpoints)}
            )

        # Step 2: 各チェックポイントで平均と信頼区間を計算
        overall_means = {}
        ci_lowers = {}
        ci_uppers = {}
        for i in range(n_checkpoints):
            values = []
            for m in per_start_means:
                if m[i] is not None:
                    values.append(m[i])
            if len(values) >= 2:
                mean_x, ci_lower, ci_upper = compute_95_ci(values)
                overall_means[i] = mean_x
                ci_lowers[i] = ci_lower
                ci_uppers[i] = ci_upper
            elif len(values) == 1:
                overall_means[i] = values[0]
                ci_lowers[i] = None
                ci_uppers[i] = None
            else:
                overall_means[i] = None
                ci_lowers[i] = None
                ci_uppers[i] = None
        return overall_means, ci_lowers, ci_uppers

    mean_AG, ci_lower_AG, ci_upper_AG = mean_ci_over_starts(results_AG_by_start)
    mean_DC, ci_lower_DC, ci_upper_DC = mean_ci_over_starts(results_DC_by_start)
    mean_RS, ci_lower_RS, ci_upper_RS = mean_ci_over_starts(results_RS_by_start)
    mean_DCR, ci_lower_DCR, ci_upper_DCR = mean_ci_over_starts(results_DCR_by_start)

    print("Final Mean Resilience Gains (with 95% CI):")
    print("AdvGreedy\n(coverage/mean/CI_width)")
    for i in range(n_checkpoints):
        print(
            f"{int(checkpoints[i] * 100)} {mean_AG[i]:.4f} {(ci_upper_AG[i] - ci_lower_AG[i]):.4f}"
        )
    print("DegreeCentrality\n(coverage/mean/CI_width)")
    for i in range(n_checkpoints):
        print(
            f"{int(checkpoints[i] * 100)} {mean_DC[i]:.4f} {(ci_upper_DC[i] - ci_lower_DC[i]):.4f}"
        )
    print("DegreeCentralityReverse\n(coverage/mean/CI_width)")
    for i in range(n_checkpoints):
        print(
            f"{int(checkpoints[i] * 100)} {mean_DCR[i]:.4f} {(ci_upper_DCR[i] - ci_lower_DCR[i]):.4f}"
        )
    print("RandomSelect\n(coverage/mean/CI_width)")
    for i in range(n_checkpoints):
        print(
            f"{int(checkpoints[i] * 100)} {mean_RS[i]:.4f} {(ci_upper_RS[i] - ci_lower_RS[i]):.4f}"
        )
    end_time = time.perf_counter()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
    # 条件をプリントするグラフデータ、パラメータなど
    print(
        f"Graph: {file}, BUDGET: {BUDGET}, N_START_ATTEMPTS: {N_START_ATTEMPTS}, N_RW_ATTEMPTS: {N_RW_ATTEMPTS}"
    )


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


def calc_upper_rg_bound():
    """与えられたグラフに対してResilience Gainの上限値を計算して返す"""
    g = graph_tools.Graph(directed=False)
    filePath = GRAPH_PATH
    lines = []
    for line in fileinput.input(files=(filePath,)):
        line = line.rstrip()
        lines.append(line)
    g.import_edge_list(lines)
    edge_list = g.export_edge_list()
    result = subprocess.run(
        ["./cpp/AdvGreedySelectAnchorStdIn", str(BUDGET)],
        input=edge_list,
        capture_output=True,
        text=True,
    )
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        print(f"AdvGreedySelectAnchorStdIn failed with return code {result.returncode}")
        return None
    anchors = result.stdout.strip().split("\n")
    upperbound = rg.resilience_gain(g, anchors)
    return upperbound


if __name__ == "__main__":
    main()

import os
import random
import randomwalk
import graph_tools
import fileinput
import subprocess
import resilience_gain as rg
import scipy.stats as stats
import numpy as np
import time


def main():
    start_time = time.perf_counter()
    os.makedirs("tmp", exist_ok=True)
    file = "graph/ba-n-500.edges"
    g = graph_tools.Graph(directed=False)
    lines = []
    for line in fileinput.input(files=(file,)):
        line = line.rstrip()
        lines.append(line)

    g.import_edge_list(lines)

    seed = 1
    rng = random.Random(seed)

    checkpoints = [0.1, 0.2, 0.3, 0.4, 0.5]  # Coverage checkpoints

    # 集計用のlist（startごとにRW試行を格納）
    n_checkpoints = len(checkpoints)
    results_AG_by_start = []
    results_DC_by_start = []
    results_RS_by_start = []


    for start_node_attempt in range(10):
        start = rng.choice(list(g.vertices()))
        agent = randomwalk.create_agent("SRW", graph=g, current=start, rng=rng)

        # startごとの結果
        results_AG = {i: [] for i in range(n_checkpoints)}
        results_DC = {i: [] for i in range(n_checkpoints)}
        results_RS = {i: [] for i in range(n_checkpoints)}

        for rw_attempt in range(10):
            print(f"START_NODE: {start_node_attempt+1}({start}), RW_ATTEMPT: {rw_attempt+1}")
            coverage = 0
            step = 0
            checkpoint_index = 0

            while checkpoint_index < len(checkpoints):
                discovered_graph = agent.get_discovered_graph_with_neighbors()
                coverage = discovered_graph.nvertices() / g.nvertices()
                if coverage >= checkpoints[checkpoint_index]:
                    ## アンカー決定
                    edge_list = discovered_graph.export_edge_list()
                    budget = 5

                    # AdvGreedy
                    result_by_adv = subprocess.run(
                        ["./cpp/AdvGreedySelectAnchorStdIn", str(budget)],
                        input=edge_list,
                        capture_output=True,
                        text=True
                    )
                    # print(result.stdout)
                    if result_by_adv.stderr:
                        print(result_by_adv.stderr)
                    
                    anchors_by_adv = result_by_adv.stdout.strip().split('\n')
                    rg_by_adv = rg.resilience_gain(
                        g,
                        anchors_by_adv
                    )

                    # DegreeCentrality
                    discovered_nodes = discovered_graph.vertices()
                    anchors_by_DC = sorted(
                        discovered_nodes,
                        key=lambda v: discovered_graph.degree(v),
                        reverse=True
                    )[:budget]
                    rg_by_DC = rg.resilience_gain(
                        g,
                        anchors_by_DC
                    )

                    # RandomSelect
                    anchors_by_RS = rng.sample(list(discovered_nodes), k=budget)
                    rg_by_RS = rg.resilience_gain(
                        g,
                        anchors_by_RS
                    )

                    # 集計用にデータを保存
                    results_AG[checkpoint_index].append(rg_by_adv)
                    results_DC[checkpoint_index].append(rg_by_DC)
                    results_RS[checkpoint_index].append(rg_by_RS)

                    checkpoint_index += 1

                agent.advance()
                step += 1

        results_AG_by_start.append(results_AG)
        results_DC_by_start.append(results_DC)
        results_RS_by_start.append(results_RS)

    # 結果を集計する（RW試行平均→start平均）
    def mean_or_none(values):
        if not values:
            print("No values to compute mean.")
            return None
        return sum(values) / len(values)   

    def mean_over_starts(results_by_start):
        per_start_means = []
        for start_results in results_by_start:
            per_start_means.append(
                {i: mean_or_none(start_results[i]) for i in range(n_checkpoints)}
            )

        overall_means = {}
        for i in range(n_checkpoints):
            values = []
            for m in per_start_means:
                if m[i] is not None:
                    values.append(m[i])
            overall_means[i] = mean_or_none(values)
        return overall_means

    mean_AG = mean_over_starts(results_AG_by_start)
    mean_DC = mean_over_starts(results_DC_by_start)
    mean_RS = mean_over_starts(results_RS_by_start)

    print("Final Mean Resilience Gains:")
    for i in range(n_checkpoints):
        print(f"{int(checkpoints[i]*100)}% coverage:")
        print(f"  AdvGreedy: {mean_AG[i]}")
        print(f"  DegreeCentrality: {mean_DC[i]}")
        print(f"  RandomSelect: {mean_RS[i]}")
    end_time = time.perf_counter()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")

def compute_95_ci(data):
    data = np.array(data)
    n = len(data)
    mean_x = np.mean(data)
    s = np.std(data, ddof=1)  # 不偏標準偏差
    SE = s / np.sqrt(n)  # 標準誤差
    t_value = stats.t.ppf(0.975, df=n-1)  # 95%信頼区間の t 値
    CI_lower = mean_x - t_value * SE
    CI_upper = mean_x + t_value * SE
    
    return mean_x, CI_lower, CI_upper



if __name__ == "__main__":
    main()

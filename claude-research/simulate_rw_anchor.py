#!/usr/bin/env python3
"""simulate_rw_anchor.py
=====================
RW種別 × アンカー選定手法 クロス比較シミュレーション。
未知グラフにおける部分グラフベースのアンカー選定で、いずれの組み合わせが
最大レジリエンス利得を得るかを検証する。

比較する次元:
  RW種別       : SRW, NBRW, VARW, SARW
  アンカー手法 : AdvGreedy, DegreeCentrality, CoreNumber,
                 DegreeCentralityReverse, RandomSelect

Usage:
    uv run python simulate_rw_anchor.py --graph graph/ba-n-1000.edges --budget 10 --n-start 30 --n-rw 10
"""

import random
import subprocess
import time
import argparse
import sys
from collections import defaultdict

import numpy as np
import scipy.stats as stats
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor

import randomwalk
import graph_tools
import resilience_gain as rg

# -------------------------------------------------------
# 定数
# -------------------------------------------------------
RW_TYPES    = ["SRW", "NBRW", "VARW", "SARW"]
METHODS     = ["AdvGreedy", "DegreeCentrality", "CoreNumber",
               "DegreeCentralityReverse", "RandomSelect"]
CHECKPOINTS = [0.1, 0.2, 0.3, 0.4, 0.5]
MAX_STEPS   = 60000  # 無限ループ防止

# RW種別ごとのシードオフセット（再現性のため）
_RW_SEED_OFF = {"SRW": 0, "NBRW": 100_000, "VARW": 200_000, "SARW": 300_000}

# -------------------------------------------------------
# ワーカー共有グローバル
# -------------------------------------------------------
_g      = None
_budget = None
_n_rw   = None


def _init(graph_lines, budget, n_rw):
    global _g, _budget, _n_rw
    _budget, _n_rw = budget, n_rw
    _g = graph_tools.Graph(directed=False)
    _g.import_edge_list(graph_lines)


def _worker(args):
    """(rw_type, start_idx, seed) を受け、全チェックポイント × 全手法の結果を返す"""
    rw_type, _, seed = args
    g      = _g
    budget = _budget
    n_ck   = len(CHECKPOINTS)
    rng    = random.Random(seed)
    start  = rng.choice(list(g.vertices()))

    # results[method][ckpt_idx] → [gain, ...]
    results = {m: {i: [] for i in range(n_ck)} for m in METHODS}

    for _ in range(_n_rw):
        agent = randomwalk.create_agent(rw_type, graph=g, current=start, rng=rng)
        ci    = 0   # 次のチェックポイントインデックス
        steps = 0

        while ci < n_ck and steps < MAX_STEPS:
            if agent.coverage_with_neighbors() >= CHECKPOINTS[ci]:
                disc   = agent.get_discovered_graph_with_neighbors()
                elist  = disc.export_edge_list()
                dnodes = list(disc.vertices())
                k      = min(budget, len(dnodes))

                # ---- 各手法の計算関数（デフォルト引数で変数キャプチャ）----
                def _adv(_el=elist, _b=budget):
                    r = subprocess.run(
                        ["./cpp/AdvGreedySelectAnchorStdIn", str(_b)],
                        input=_el, capture_output=True, text=True)
                    if r.returncode != 0 or not r.stdout.strip():
                        return 0
                    return rg.resilience_gain(g, r.stdout.strip().split("\n"))

                def _dc(_dn=dnodes, _d=disc, _k=k):
                    a = sorted(_dn, key=lambda v: _d.degree(v), reverse=True)[:_k]
                    return rg.resilience_gain(g, a)

                def _cn(_dn=dnodes, _d=disc, _k=k):
                    cores = rg.core_decomposition(_d)
                    a = sorted(_dn, key=lambda v: cores[v], reverse=True)[:_k]
                    return rg.resilience_gain(g, a)

                def _dcr(_dn=dnodes, _d=disc, _k=k):
                    a = sorted(_dn, key=lambda v: _d.degree(v))[:_k]
                    return rg.resilience_gain(g, a)

                def _rs(_dn=dnodes, _k=k):
                    a = rng.sample(_dn, k=_k)
                    return rg.resilience_gain(g, a)

                # 5手法を並列実行
                with ThreadPoolExecutor(max_workers=5) as ex:
                    futs = {
                        "AdvGreedy":              ex.submit(_adv),
                        "DegreeCentrality":       ex.submit(_dc),
                        "CoreNumber":             ex.submit(_cn),
                        "DegreeCentralityReverse":ex.submit(_dcr),
                        "RandomSelect":           ex.submit(_rs),
                    }
                    for m in METHODS:
                        results[m][ci].append(futs[m].result())

                ci += 1
            agent.advance()
            steps += 1

    return rw_type, results


# -------------------------------------------------------
# 統計・集約
# -------------------------------------------------------
def ci95(data):
    """95%信頼区間を返す (mean, lower, upper)"""
    arr = np.array(data, dtype=float)
    n   = len(arr)
    mu  = float(np.mean(arr))
    if n < 2:
        return mu, None, None
    se  = float(np.std(arr, ddof=1)) / np.sqrt(n)
    t   = stats.t.ppf(0.975, df=n - 1)
    return mu, mu - t * se, mu + t * se


def upper_bound(graph_lines, budget):
    """全グラフに対する上限値 (AdvGreedy on full graph)"""
    g = graph_tools.Graph(directed=False)
    g.import_edge_list(graph_lines)
    r = subprocess.run(
        ["./cpp/AdvGreedySelectAnchorStdIn", str(budget)],
        input=g.export_edge_list(), capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return 1  # fallback
    return rg.resilience_gain(g, r.stdout.strip().split("\n"))


# -------------------------------------------------------
# 結果のフォーマット・書き込み
# -------------------------------------------------------
def format_results(tbl, ub, args, elapsed):
    out = []

    def emit(s=""):
        out.append(s)

    emit("=" * 100)
    emit("  シミュレーション結果: RW種別 × アンカー選定手法の比較")
    emit("=" * 100)
    emit(f"  グラフ          : {args.graph}")
    emit(f"  バジェット (k)  : {args.budget}")
    emit(f"  開始点数        : {args.n_start}")
    emit(f"  RW試行/開始点   : {args.n_rw}")
    emit(f"  上限値 (UB)     : {ub}  (全グラフに対するAdvGreedy)")
    emit(f"  実行時間        : {elapsed:.1f}s")
    emit("=" * 100)
    emit("")

    # ---- Per-RW テーブル (正規化値 = raw / UB) ----
    emit("  *** 正規化レジリエンス利得 (UBで割り算)  ±は95%信頼区間幅 ***")
    emit("")

    for rw in RW_TYPES:
        emit(f"--- {rw} ---")
        hdr = f"{'Cov':>6} |"
        for m in METHODS:
            hdr += f" {m:<27}|"
        emit(hdr)
        emit("-" * len(hdr))
        for ci, cp in enumerate(CHECKPOINTS):
            row = f"{int(cp*100):>5}% |"
            for m in METHODS:
                key = (rw, m, ci)
                if key in tbl:
                    mu, lo, hi = tbl[key]
                    mn = mu / ub
                    if lo is not None:
                        w  = (hi - lo) / ub
                        row += f" {mn:.4f}  (±{w:.4f})           |"
                    else:
                        row += f" {mn:.4f}  (n=1)               |"
                else:
                    row += f" {'N/A':<27}|"
            emit(row)
        emit("")

    # ---- 要約: 各カバレッジで最高手法 ----
    emit("")
    emit("=" * 100)
    emit("  要約: 各RW × カバレッジで最も高いレジリエンス利得の手法")
    emit("=" * 100)
    shdr = f"{'Cov':>6} |"
    for rw in RW_TYPES:
        shdr += f" {rw:<28}|"
    emit(shdr)
    emit("-" * len(shdr))
    for ci, cp in enumerate(CHECKPOINTS):
        row = f"{int(cp*100):>5}% |"
        for rw in RW_TYPES:
            best_m, best_v = None, -1
            for m in METHODS:
                key = (rw, m, ci)
                if key in tbl and tbl[key][0] > best_v:
                    best_v = tbl[key][0]
                    best_m = m
            if best_m:
                row += f" {best_m[:15]}: {best_v/ub:.4f}         |"
            else:
                row += f" {'N/A':<28}|"
        emit(row)
    emit("")

    # ---- 生の値 ----
    emit("")
    emit("=" * 100)
    emit("  生の値 (正規化なし, ±は95%CI幅の半分)")
    emit("=" * 100)
    for rw in RW_TYPES:
        emit(f"--- {rw} (raw) ---")
        hdr = f"{'Cov':>6} |"
        for m in METHODS:
            hdr += f" {m:<18}|"
        emit(hdr)
        emit("-" * len(hdr))
        for ci, cp in enumerate(CHECKPOINTS):
            row = f"{int(cp*100):>5}% |"
            for m in METHODS:
                key = (rw, m, ci)
                if key in tbl:
                    mu, lo, hi = tbl[key]
                    if lo is not None:
                        row += f" {mu:7.2f} ±{(hi-lo)/2:5.2f}   |"
                    else:
                        row += f" {mu:7.2f}            |"
                else:
                    row += f" {'N/A':<18}|"
            emit(row)
        emit("")

    return out


def analyze_results(tbl, ub):
    """結果から自動分析を行い、知見のサマリーを生成する"""
    lines = []
    lines.append("")
    lines.append("=" * 100)
    lines.append("  自動分析・知見サマリー")
    lines.append("=" * 100)

    # 1. 全体で最も高いレジリエンス手法は？
    lines.append("")
    lines.append("  [1] 全体で最も高い正規化レジリエンス利得を達成した組み合わせ:")
    best_combo = None
    best_val   = -1
    for rw in RW_TYPES:
        for m in METHODS:
            for ci in range(len(CHECKPOINTS)):
                key = (rw, m, ci)
                if key in tbl and tbl[key][0] > best_val:
                    best_val = tbl[key][0]
                    best_combo = (rw, m, ci)
    if best_combo:
        rw, m, ci = best_combo
        lines.append(f"       → {rw} + {m} @ {int(CHECKPOINTS[ci]*100)}% カバレッジ: {best_val/ub:.4f}")

    # 2. 各RW種別で最も高いカバレッジ(50%)での最高手法
    lines.append("")
    lines.append("  [2] 50%カバレッジで各RW種別の最高手法:")
    ci_50 = CHECKPOINTS.index(0.5)
    for rw in RW_TYPES:
        best_m, best_v = None, -1
        for m in METHODS:
            key = (rw, m, ci_50)
            if key in tbl and tbl[key][0] > best_v:
                best_v = tbl[key][0]
                best_m = m
        if best_m:
            lines.append(f"       {rw:6s}: {best_m} ({best_v/ub:.4f})")

    # 3. 各アンカー手法について、最も高いカバレッジでの平均(全RW)
    lines.append("")
    lines.append("  [3] 50%カバレッジで各アンカー手法の全RW種別平均:")
    ci_50 = CHECKPOINTS.index(0.5)
    method_avg = {}
    for m in METHODS:
        vals = []
        for rw in RW_TYPES:
            key = (rw, m, ci_50)
            if key in tbl:
                vals.append(tbl[key][0])
        if vals:
            method_avg[m] = np.mean(vals)
    for m, v in sorted(method_avg.items(), key=lambda x: -x[1]):
        lines.append(f"       {m:<30s}: {v/ub:.4f}")

    # 4. RW種別が利得に与える影響(AdvGreedy手法で比較)
    lines.append("")
    lines.append("  [4] AdvGreedy手法でのRW種別比較 (各カバレッジ):")
    lines.append(f"       {'Cov':>5} | " + " | ".join(f"{rw:>8}" for rw in RW_TYPES))
    lines.append("       " + "-" * 55)
    for ci, cp in enumerate(CHECKPOINTS):
        row = f"       {int(cp*100):>4}% | "
        for rw in RW_TYPES:
            key = (rw, "AdvGreedy", ci)
            if key in tbl:
                row += f" {tbl[key][0]/ub:>7.4f} | "
            else:
                row += f" {'N/A':>7} | "
        lines.append(row)

    # 5. DegreeCentralityの傾向(BA vs ER で異なる挙動があるはず)
    lines.append("")
    lines.append("  [5] DegreeCentralityの傾向:")
    dc_vals = []
    for rw in RW_TYPES:
        key_lo = (rw, "DegreeCentrality", 0)   # 10%
        key_hi = (rw, "DegreeCentrality", 4)   # 50%
        if key_lo in tbl and key_hi in tbl:
            lo_v = tbl[key_lo][0] / ub
            hi_v = tbl[key_hi][0] / ub
            trend = "上昇" if hi_v > lo_v else "低下" if hi_v < lo_v else "横移動"
            lines.append(f"       {rw}: 10%→50% で {lo_v:.4f}→{hi_v:.4f} ({trend})")

    # 6. CoreNumberとAdvGreedyの比較
    lines.append("")
    lines.append("  [6] CoreNumber vs AdvGreedy (正規化値の差分):")
    for rw in RW_TYPES:
        diffs = []
        for ci in range(len(CHECKPOINTS)):
            k_cn  = (rw, "CoreNumber",  ci)
            k_adv = (rw, "AdvGreedy",   ci)
            if k_cn in tbl and k_adv in tbl:
                diffs.append(tbl[k_cn][0] / ub - tbl[k_adv][0] / ub)
        if diffs:
            avg_diff = np.mean(diffs)
            lines.append(f"       {rw}: CoreNumber - AdvGreedy の平均差分 = {avg_diff:+.4f}")

    lines.append("")
    return lines


# -------------------------------------------------------
# メイン
# -------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="RW × Anchor method comparison")
    parser.add_argument("--graph",   type=str,  default="graph/ba-n-1000.edges")
    parser.add_argument("--budget",  type=int,  default=10)
    parser.add_argument("--n-start", type=int,  default=30)
    parser.add_argument("--n-rw",    type=int,  default=10)
    parser.add_argument("--output",  type=str,  default=None)
    a = parser.parse_args()

    if a.output is None:
        import os
        base = os.path.splitext(os.path.basename(a.graph))[0]
        a.output = f"results_{base}_b{a.budget}.txt"

    t0 = time.perf_counter()

    # --- グラフ読み込み ---
    with open(a.graph) as f:
        lines = [l.rstrip() for l in f]

    # 連結性チェック
    g = graph_tools.Graph(directed=False)
    g.import_edge_list(lines)
    if not g.is_connected():
        print("[INFO] 非連結グラフ — 最大連結成分を使用", flush=True)
        gcc  = g.maximal_component()
        lines = gcc.export_edge_list().strip().split("\n")

    ub = upper_bound(lines, a.budget)
    print(f"[INFO] 上限値 (UB) = {ub}", flush=True)

    # --- 作業単位の生成 ---
    work = []
    for rw in RW_TYPES:
        for i in range(a.n_start):
            seed = 42 + _RW_SEED_OFF[rw] + i * 1000
            work.append((rw, i, seed))

    nw = min(cpu_count(), len(work))
    print(f"[INFO] Workers={nw}, Units={len(work)} "
          f"({len(RW_TYPES)} RW × {a.n_start} starts × {a.n_rw} RW/start)", flush=True)

    # --- 並列実行 ---
    with Pool(processes=nw, initializer=_init,
              initargs=(lines, a.budget, a.n_rw)) as pool:
        raw = pool.map(_worker, work)

    # --- 結果集約 ---
    by_rw = defaultdict(list)
    for rw_type, res in raw:
        by_rw[rw_type].append(res)

    # tbl[(rw, method, ckpt_idx)] = (mean_raw, lo_raw, hi_raw)
    tbl = {}
    for rw in RW_TYPES:
        for m in METHODS:
            for ci in range(len(CHECKPOINTS)):
                per_start = []
                for sr in by_rw[rw]:
                    vals = sr[m][ci]
                    if vals:
                        per_start.append(float(np.mean(vals)))
                if per_start:
                    tbl[(rw, m, ci)] = ci95(per_start)

    elapsed = time.perf_counter() - t0

    # --- 結果フォーマットと書き込み ---
    out = format_results(tbl, ub, a, elapsed)
    analysis = analyze_results(tbl, ub)
    out.extend(analysis)

    # 標準出力
    for line in out:
        print(line, flush=True)

    # ファイル書き込み
    with open(a.output, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"\n[INFO] 結果を {a.output} に書き込みました", flush=True)


if __name__ == "__main__":
    main()

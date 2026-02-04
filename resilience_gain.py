#!/usr/bin/python3
import sys

sys.path.insert(0, "vendor")

import graph_tools
import pathutil


def core_decomposition(g, A=[]):
    deg = {v: g.degree(v) for v in g.vertices()}
    n = len(deg)
    md = max(deg.values(), default=0)  # 最大次数

    for v in A:
        deg[v] = md

    # --- 2. バケット (bin-sort) 準備 ---
    bin_start = [0] * (md + 1)  # 各次数 d のバケット開始位置
    for d in deg.values():
        bin_start[d] += 1  # バケットに頂点数をカウント

    # prefix sum で「開始位置」に変換
    start = 0
    for d in range(md + 1):
        cnt = bin_start[d]
        bin_start[d] = start
        start += cnt

    vert: list[int] = [None] * n  # i 番目に並ぶ頂点 ID
    pos: dict[int, int] = {}  # 頂点 v の vert 中インデックス

    for v, d in deg.items():  # 頂点をバケット順に配置
        idx = bin_start[d]
        vert[idx] = v
        pos[v] = idx
        bin_start[d] += 1  # バケットの先頭を右へ 1

    # bin_start をもう一度「開始位置」に戻す
    for d in range(md, 0, -1):
        bin_start[d] = bin_start[d - 1]
    bin_start[0] = 0

    # --- 3. メインループ ---
    for i in range(n):
        v = vert[i]
        for u in g.neighbors(v):
            if deg[u] > deg[v]:  # 高次数側のみ処理
                du = deg[u]
                pu = pos[u]
                pw = bin_start[du]  # 同次数バケットの先頭
                w = vert[pw]

                if u != w:  # u をバケット先頭へ swap
                    vert[pu], vert[pw] = w, u
                    pos[u], pos[w] = pw, pu

                bin_start[du] += 1  # バケット先頭を 1 つ右へ
                deg[u] -= 1  # u の次数をデクリメント
    return deg


def resilience_gain(g, A):
    A = frozenset(A)
    c0 = core_decomposition(g)
    cA = core_decomposition(g, A)

    gain = 0
    for v in g.vertices():
        if v in A or cA[v] > c0[v]:
            gain += 1
    return gain


def main():
    filename = sys.argv[1:3]
    g = graph_tools.Graph(directed=False)
    g.import_edge_list(pathutil.Path(filename[0]).lines())

    A = []
    with open(filename[1], "r") as f:
        for line in f:
            A.append(line.strip())

    print(resilience_gain(g, A))


if __name__ == "__main__":
    main()

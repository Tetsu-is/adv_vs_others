"""非連結グラフのedge listから最大連結成分(GCC)のedge listを標準出力に吐き出す。
元が連結の場合はエラーで終了する。
"""

import sys
import argparse
import networkx as nx


def main():
    parser = argparse.ArgumentParser(description="非連結グラフのedge listから最大連結成分を抽出する")
    parser.add_argument("input", nargs="?", default="-", help="入力edge listファイル (デフォルト: stdin)")
    args = parser.parse_args()

    G = nx.read_edgelist(sys.stdin if args.input == "-" else args.input)

    if nx.is_connected(G):
        print(f"Error: graph is already connected ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges).", file=sys.stderr)
        sys.exit(1)

    gcc_nodes = max(nx.connected_components(G), key=len)
    gcc = G.subgraph(gcc_nodes)

    print(f"# {nx.number_connected_components(G)} components found. GCC size: {len(gcc_nodes)} nodes.", file=sys.stderr)

    nx.write_edgelist(gcc, sys.stdout.buffer, data=False)


if __name__ == "__main__":
    main()

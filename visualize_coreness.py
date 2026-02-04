#!/usr/bin/env python3
"""
グラフのコアネスを視覚化するスクリプト

使用方法:
    python visualize_coreness.py <edgelist_file>

例:
    python visualize_coreness.py network.edges
"""

import sys
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np


def load_graph_from_edgelist(filepath):
    """
    エッジリストファイルからグラフを読み込む
    
    Args:
        filepath: エッジリストファイルのパス
        
    Returns:
        networkx.Graph: 読み込まれたグラフ
    """
    try:
        G = nx.read_edgelist(filepath)
        print(f"グラフを読み込みました: {len(G.nodes())}ノード, {len(G.edges())}エッジ")
        return G
    except Exception as e:
        print(f"エラー: ファイルの読み込みに失敗しました: {e}")
        sys.exit(1)


def calculate_coreness(G):
    """
    各ノードのコアネスを計算する
    
    Args:
        G: networkx.Graph
        
    Returns:
        dict: ノードIDをキー、コアネス値をバリューとする辞書
    """
    coreness = nx.core_number(G)
    print(f"コアネスの範囲: {min(coreness.values())} - {max(coreness.values())}")
    return coreness


def visualize_coreness(G, coreness, output_file='coreness_visualization.png'):
    """
    コアネスを色で表現してグラフを視覚化する
    
    Args:
        G: networkx.Graph
        coreness: 各ノードのコアネス値の辞書
        output_file: 出力ファイル名
    """
    # レイアウトの計算
    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
    
    # コアネス値のリスト（ノード順に対応）
    coreness_values = [coreness[node] for node in G.nodes()]
    
    # カラーマップの設定（青→赤）
    cmap = plt.colormaps.get_cmap('coolwarm')  # 青(低い値)から赤(高い値)
    
    # 正規化
    vmin = min(coreness_values)
    vmax = max(coreness_values)
    
    # 図の作成
    plt.figure(figsize=(12, 10))
    
    # ノードの描画
    nodes = nx.draw_networkx_nodes(
        G, pos,
        node_color=coreness_values,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        node_size=100,
        alpha=0.9
    )
    
    # エッジの描画
    nx.draw_networkx_edges(
        G, pos,
        alpha=0.3,
        width=1.0,
        edge_color='gray'
    )
    
    # ラベルの描画（ノード数が少ない場合のみ）
    if len(G.nodes()) <= 50:
        nx.draw_networkx_labels(
            G, pos,
            font_size=8,
            font_color='black'
        )
    
    # カラーバーの追加
    cbar = plt.colorbar(nodes, label='Coreness')
    cbar.ax.tick_params(labelsize=10)
    
    plt.title('Graph Coreness Visualization', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    # 保存
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"視覚化を保存しました: {output_file}")
    
    # 表示
    plt.show()


def print_coreness_statistics(coreness):
    """
    コアネスの統計情報を表示する
    
    Args:
        coreness: 各ノードのコアネス値の辞書
    """
    values = list(coreness.values())
    print("\n=== コアネス統計情報 ===")
    print(f"最小値: {min(values)}")
    print(f"最大値: {max(values)}")
    print(f"平均値: {np.mean(values):.2f}")
    print(f"中央値: {np.median(values):.2f}")
    print(f"標準偏差: {np.std(values):.2f}")
    
    # コアネスごとのノード数
    from collections import Counter
    core_counts = Counter(values)
    print("\nコアネスごとのノード数:")
    for core in sorted(core_counts.keys()):
        print(f"  Coreness {core}: {core_counts[core]}ノード")


def main():
    """メイン関数"""
    # コマンドライン引数のチェック
    if len(sys.argv) != 2:
        print("使用方法: python visualize_coreness.py <edgelist_file>")
        print("例: python visualize_coreness.py network.edges")
        sys.exit(1)
    
    edgelist_file = sys.argv[1]
    
    # グラフの読み込み
    print(f"エッジリストファイルを読み込んでいます: {edgelist_file}")
    G = load_graph_from_edgelist(edgelist_file)
    
    # コアネスの計算
    print("\nコアネスを計算しています...")
    coreness = calculate_coreness(G)
    
    # 統計情報の表示
    print_coreness_statistics(coreness)
    
    # 視覚化
    print("\nグラフを視覚化しています...")
    visualize_coreness(G, coreness)
    
    print("\n完了しました!")


if __name__ == "__main__":
    main()
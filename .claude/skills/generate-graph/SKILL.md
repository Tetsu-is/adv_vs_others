---
name: generate-graph
description: graphgenコマンドをつかってグラフを生成するスキル
---

## グラフ生成をするときはgraphgenコマンドを使ってエッジリストを生成してgraph/に格納します。
1. graphgenコマンドで欲しいグラフのエッジリストを生成します。例えば、10ノードのランダムグラフを生成する場合は以下のようにします。グラフのファイル名にはノード数エッジ数などのパラメータを含めてください。
`graphgen -u -t random 10 15 -o edges > graph/random-n10-e10.edgelist`

2. 生成したエッジリストを確認します。
`cat graph/random-n10-e10.edgelist`


## graphgenの使い方は以下を参考にしてください
```
graphgen -h
option -h not recognized
usage: graphgen [-du] [-s seed] [-t type] [-s seed] [-o format] params...
  -d         generate directed graph
  -u         generate undirected graph (default)
  -t type    specify graph type (ba/barabasi/barandom/btree/configuration/db/degree_bounded/er/erdos_renyi/general_ba/latent/lattice/li_maini/preset/random/random_sparse/regular/ring/star/tree/treeba/voronoi)
             parameters (defaults):
                 random/random_sparse: [N [E [no_multiedge]]] (N=20, E=10)
                 erdos_renyi/er: [N [p]] (N=10, p=0.5)
                 barabasi/ba: [N [m [m0]]] (N=10, m=2, m0=2)
                 barandom: [N [E [m0]]] (N=10, E=10, m0=2)
                 ring: [N [step]] (N=10, step=1)
                 tree: [N] (N=10)
                 btree: [N] (N=10)
                 treeba: [N [alpha]] (N=10, alpha=1)
                 general_ba: [N [m [gamma [m0]]]] (N=10, m=2, gamma=3, m0=2)
                 latent: [N [E [error_ratio [confer [dist [alpha]]]]]]
                     (N=10, E=20, error_ratio=0, confer=linear, dist=normal, alpha=10)
                     confer: abs/binary/linear/sigmoid
                     dist: uniform/normal/exponential
                 lattice: [dim [n [is_torus]]] (dim=2, n=5, is_torus=False)
                 voronoi: [npoints [width [height]]] (npoints=10, width=1, height=1)
                 degree_bounded/db: [N [E]] (N=10, E=20)
                 configuration [degree_seq] (degree_seq=6,5,4,3,3,3,2,2,1,1)
                 regular: [N [k]] (N=10, k=3)
                 li_maini: [T [M [m0 [m [alpha [n]]]]]] (T=200, M=4, m0=4, m=1, alpha=.1, n=1)
                 preset: [n] (n=0)
                 star: [n] (n=10)
  -s seed    specify random number seed
  -o format  output graph format (cell/dot/edges)
```
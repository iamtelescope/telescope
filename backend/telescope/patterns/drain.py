"""The Drain log template miner with Drain3's default settings, without persistence or an LRU.

Ported from IBM Drain3 `drain3/drain.py` (MIT), as HyperDX `common-utils/src/drain/drain.ts` does.
"""

PARAM = "<*>"


class Cluster:
    __slots__ = ["id", "tokens", "size"]

    def __init__(self, cluster_id, tokens):
        self.id = cluster_id
        self.tokens = tuple(tokens)
        self.size = 1

    @property
    def template(self):
        return " ".join(self.tokens)


class Node:
    __slots__ = ["children", "cluster_ids"]

    def __init__(self):
        self.children = {}
        self.cluster_ids = []


def _has_digit(token):
    return any(c.isdigit() for c in token)


class Drain:
    def __init__(self, depth=4, sim_th=0.4, max_children=100):
        self.max_node_depth = depth - 2
        self.sim_th = sim_th
        self.max_children = max_children
        self.root = Node()
        self.clusters = {}

    def _tree_search(self, tokens):
        node = self.root.children.get(str(len(tokens)))
        if node is None:
            return None
        if not tokens:
            return self.clusters[node.cluster_ids[0]]
        depth = 1
        for token in tokens:
            if depth >= self.max_node_depth or depth == len(tokens):
                break
            node = node.children.get(token) or node.children.get(PARAM)
            if node is None:
                return None
            depth += 1
        return self._fast_match(node.cluster_ids, tokens)

    def _fast_match(self, cluster_ids, tokens):
        best, best_sim, best_params = None, -1, -1
        for cluster_id in cluster_ids:
            cluster = self.clusters[cluster_id]
            same = params = 0
            for t1, t2 in zip(cluster.tokens, tokens):
                if t1 == PARAM:
                    params += 1
                elif t1 == t2:
                    same += 1
            sim = same / len(tokens)
            if sim > best_sim or (sim == best_sim and params > best_params):
                best, best_sim, best_params = cluster, sim, params
        return best if best_sim >= self.sim_th else None

    def _add_to_tree(self, cluster):
        tokens = cluster.tokens
        node = self.root.children.setdefault(str(len(tokens)), Node())
        if not tokens:
            node.cluster_ids = [cluster.id]
            return
        depth = 1
        for token in tokens:
            if depth >= self.max_node_depth or depth >= len(tokens):
                node.cluster_ids.append(cluster.id)
                return
            children = node.children
            if token in children:
                node = children[token]
            elif _has_digit(token):
                node = children.setdefault(PARAM, Node())
            elif PARAM in children:
                if len(children) < self.max_children:
                    node = children.setdefault(token, Node())
                else:
                    node = children[PARAM]
            elif len(children) + 1 < self.max_children:
                node = children.setdefault(token, Node())
            elif len(children) + 1 == self.max_children:
                node = children.setdefault(PARAM, Node())
            else:
                node = children[PARAM]
            depth += 1

    def add(self, text):
        """Cluster one message (already normalized); returns its cluster."""
        tokens = text.strip().split()
        cluster = self._tree_search(tokens)
        if cluster is None:
            cluster = Cluster(len(self.clusters) + 1, tokens)
            self.clusters[cluster.id] = cluster
            self._add_to_tree(cluster)
            return cluster
        cluster.tokens = tuple(
            PARAM if t1 != t2 else t1 for t1, t2 in zip(cluster.tokens, tokens)
        )
        cluster.size += 1
        return cluster

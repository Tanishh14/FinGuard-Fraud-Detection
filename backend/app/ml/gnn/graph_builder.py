import torch
from torch_geometric.data import Data

def build_graph(node_features, edge_index):
    """
    node_features: Tensor [num_nodes, feature_dim]
    edge_index: Tensor [2, num_edges]
    """
    return Data(
        x=node_features.float(),
        edge_index=edge_index.long(),
    )

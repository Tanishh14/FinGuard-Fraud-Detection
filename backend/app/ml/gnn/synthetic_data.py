import torch
import random
import numpy as np


def generate_synthetic_graph(
    num_accounts: int = 1000,
    fraud_ratio: float = 0.05,
    seed: int = 42,
):
    """
    Generates a synthetic fraud graph for GNN training.
    Nodes = accounts
    Edges = shared devices / merchants / transfers (simulated)
    """

    random.seed(seed)
    np.random.seed(seed)

    num_fraud = int(num_accounts * fraud_ratio)
    fraud_accounts = set(random.sample(range(num_accounts), num_fraud))

    node_features = []
    labels = []

    # =========================
    # NODE FEATURE GENERATION
    # =========================
    for i in range(num_accounts):
        is_fraud = i in fraud_accounts

        # Behavioral stats
        avg_tx_amount = (
            np.random.normal(600, 80)
            if not is_fraud
            else np.random.normal(1800, 300)
        )

        tx_count_24h = (
            np.random.poisson(6)
            if not is_fraud
            else np.random.poisson(18)
        )

        tx_count_7d = tx_count_24h * np.random.randint(4, 7)

        unique_merchants = (
            np.random.randint(2, 6)
            if not is_fraud
            else np.random.randint(6, 12)
        )

        unique_devices = (
            np.random.randint(1, 3)
            if not is_fraud
            else np.random.randint(2, 5)
        )

        # AE / IF anomaly summaries (overlapping distributions)
        ae_mean = (
            np.random.uniform(0.05, 0.15)
            if not is_fraud
            else np.random.uniform(0.20, 0.40)
        )
        ae_max = ae_mean * np.random.uniform(1.1, 1.4)

        if_mean = (
            np.random.uniform(0.05, 0.15)
            if not is_fraud
            else np.random.uniform(0.20, 0.40)
        )
        if_max = if_mean * np.random.uniform(1.1, 1.4)

        node_features.append([
            avg_tx_amount,
            tx_count_24h,
            tx_count_7d,
            unique_merchants,
            unique_devices,
            ae_mean,
            ae_max,
            if_mean,
            if_max,
        ])

        labels.append(1 if is_fraud else 0)

    # =========================
    # EDGE GENERATION
    # =========================
    edges = []

    # Normal random interactions
    for _ in range(num_accounts * 2):
        a, b = random.sample(range(num_accounts), 2)
        edges.append((a, b))
        edges.append((b, a))

    # Fraud rings (moderate density)
    fraud_list = list(fraud_accounts)
    for i in fraud_list:
        for j in fraud_list:
            if i != j and random.random() < 0.4:
                edges.append((i, j))
                edges.append((j, i))

    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    return (
        torch.tensor(node_features, dtype=torch.float),
        edge_index,
        torch.tensor(labels, dtype=torch.float),
    )

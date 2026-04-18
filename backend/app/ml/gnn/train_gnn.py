import torch
from torch.optim import Adam
from sklearn.metrics import roc_auc_score

from app.ml.gnn.model import FraudGNN
from app.ml.gnn.synthetic_data import generate_synthetic_graph

def train_gnn():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    node_features, edge_index, labels = generate_synthetic_graph()

    node_features = (node_features - node_features.mean(0)) / (node_features.std(0) + 1e-6)
    edge_index = edge_index.to(device)
    labels = labels.to(device)

    model = FraudGNN(node_features.size(1)).to(device)
    optimizer = Adam(model.parameters(), lr=1e-3)
    pos_weight = torch.tensor([labels.size(0) / labels.sum()]).to(device)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)


    for epoch in range(100):
        model.train()
        optimizer.zero_grad()

        preds = model(node_features, edge_index)
        loss = criterion(preds, labels)

        loss.backward()
        optimizer.step()

        if epoch % 10 == 0:
            auc = roc_auc_score(
                labels.detach().cpu().numpy(),
                preds.detach().cpu().numpy()
            )
            print(f"Epoch {epoch:03d} | Loss: {loss:.4f} | AUC: {auc:.4f}")

    torch.save(model.state_dict(), "ml_models/gnn.pt")
    print("✅ GNN model saved")

if __name__ == "__main__":
    train_gnn()

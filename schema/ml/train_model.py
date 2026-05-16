import os
os.environ["TORCH_ONNX_USE_LEGACY_EXPORTER"] = "1"
import torch
import torch.nn as nn
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report

# -------------------------
# LOAD DATA
# -------------------------

df = pd.read_csv("dataset.csv")

X = df.drop("label", axis=1).values
y = df["label"].values

# -------------------------
# TRAIN TEST SPLIT
# -------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

X_train = torch.tensor(X_train, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)

X_test = torch.tensor(X_test, dtype=torch.float32)
y_test = torch.tensor(y_test, dtype=torch.float32).view(-1, 1)

# -------------------------
# CLASS BALANCE
# -------------------------

num_safe = (y_train == 1).sum().item()
num_unsafe = (y_train == 0).sum().item()

print(f"\nSafe samples: {num_safe}, Unsafe samples: {num_unsafe}")

weight_safe = num_unsafe / (num_safe + num_unsafe)
weight_unsafe = num_safe / (num_safe + num_unsafe)

# -------------------------
# MODEL (ZK SAFE)
# -------------------------

class JudgeNN(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 1)   # 🔥 NO SIGMOID
        )

    def forward(self, x):
        return self.net(x)


model = JudgeNN(input_dim=X.shape[1])

# -------------------------
# TRAINING
# -------------------------

optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
epochs = 50

for epoch in range(epochs):

    logits = model(X_train)

    weights = torch.where(
        y_train == 1,
        torch.tensor(weight_safe),
        torch.tensor(weight_unsafe)
    )

    loss = nn.functional.binary_cross_entropy_with_logits(
        logits, y_train, weight=weights
    )

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if epoch % 5 == 0:
        print(f"Epoch {epoch}, Loss: {loss.item():.4f}")

# -------------------------
# EVALUATION
# -------------------------

with torch.no_grad():
    logits = model(X_test)
    probs = torch.sigmoid(logits)  # apply sigmoid ONLY here

y_true = y_test.int().numpy()

# -------------------------
# THRESHOLD TUNING
# -------------------------

best_threshold = 0.5
best_score = 0

print("\n--- Threshold Tuning ---")

for t in [0.5, 0.6, 0.7, 0.8]:

    preds = (probs >= t).int().numpy()
    cm = confusion_matrix(y_true, preds)

    TN, FP, FN, TP = cm.ravel()

    unsafe_recall = TN / (TN + FP)
    accuracy = (TP + TN) / (TP + TN + FP + FN)

    score = 0.7 * unsafe_recall + 0.3 * accuracy

    print(f"\nThreshold: {t}")
    print(f"Accuracy: {accuracy:.3f}")
    print(f"Unsafe Recall: {unsafe_recall:.3f}")
    print(f"Score: {score:.3f}")

    if score > best_score:
        best_score = score
        best_threshold = t

if best_threshold > 0.7:
    print("\n⚠️ Overriding to 0.7")
    best_threshold = 0.7

print(f"\n✅ Final Threshold: {best_threshold}")

# -------------------------
# FINAL EVALUATION
# -------------------------

preds = (probs >= best_threshold).int().numpy()
cm = confusion_matrix(y_true, preds)

print("\nConfusion Matrix:")
print(cm)

TN, FP, FN, TP = cm.ravel()

accuracy = (TP + TN) / (TP + TN + FP + FN)
unsafe_recall = TN / (TN + FP)
safe_recall = TP / (TP + FN)

print(f"\nAccuracy: {accuracy * 100:.2f}%")
print(f"🔥 Unsafe Recall: {unsafe_recall * 100:.2f}%")
print(f"Safe Recall: {safe_recall * 100:.2f}%")

print("\nClassification Report:")
print(classification_report(y_true, preds))

# -------------------------
# SAVE MODEL
# -------------------------

torch.save(model.state_dict(), "model.pth")

# -------------------------
# EXPORT TO ONNX (EZKL SAFE)
# -------------------------

import torch.onnx

model.eval()

dummy_input = torch.randn(1, X.shape[1])

# 🔥 CRITICAL FIX: disable new exporter
torch.onnx.export(
    model,
    dummy_input,
    "model_raw.onnx",
    opset_version=13,
    input_names=["input"],
    output_names=["output"],
    dynamic_axes=None,
    do_constant_folding=True,
    export_params=True,
    operator_export_type=torch.onnx.OperatorExportTypes.ONNX,  # 🔥 KEY
    training=torch.onnx.TrainingMode.EVAL
)

print("\n✅ Exported model_raw.onnx (FORCED LEGACY MODE)")
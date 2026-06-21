import torch
import onnx
from onnx import helper, TensorProto
import numpy as np

# -------------------------
# CONFIG
# -------------------------

INPUT_DIM = 8  # ⚠️ must match your dataset

# -------------------------
# LOAD TRAINED WEIGHTS
# -------------------------

state_dict = torch.load("model.pth", map_location="cpu")

# 🔥 FIX 1: TRANSPOSE WEIGHTS FOR MATMUL
w1 = state_dict["net.0.weight"].numpy().T
b1 = state_dict["net.0.bias"].numpy()

w2 = state_dict["net.2.weight"].numpy().T
b2 = state_dict["net.2.bias"].numpy()

w3 = state_dict["net.4.weight"].numpy().T
b3 = state_dict["net.4.bias"].numpy()

# -------------------------
# DEFINE INPUT / OUTPUT
# -------------------------

input_tensor = helper.make_tensor_value_info(
    "input", TensorProto.FLOAT, [1, INPUT_DIM]
)

output_tensor = helper.make_tensor_value_info(
    "output", TensorProto.FLOAT, [1, 1]
)

# -------------------------
# INITIALIZERS
# -------------------------

init_w1 = helper.make_tensor("w1", TensorProto.FLOAT, w1.shape, w1.flatten())
init_b1 = helper.make_tensor("b1", TensorProto.FLOAT, b1.shape, b1)

init_w2 = helper.make_tensor("w2", TensorProto.FLOAT, w2.shape, w2.flatten())
init_b2 = helper.make_tensor("b2", TensorProto.FLOAT, b2.shape, b2)

init_w3 = helper.make_tensor("w3", TensorProto.FLOAT, w3.shape, w3.flatten())
init_b3 = helper.make_tensor("b3", TensorProto.FLOAT, b3.shape, b3)

# -------------------------
# NODES (EZKL SAFE)
# -------------------------

# Layer 1
matmul1 = helper.make_node("MatMul", ["input", "w1"], ["m1"])
add1 = helper.make_node("Add", ["m1", "b1"], ["h1"])
relu1 = helper.make_node("Relu", ["h1"], ["a1"])

# Layer 2
matmul2 = helper.make_node("MatMul", ["a1", "w2"], ["m2"])
add2 = helper.make_node("Add", ["m2", "b2"], ["h2"])
relu2 = helper.make_node("Relu", ["h2"], ["a2"])

# Layer 3
matmul3 = helper.make_node("MatMul", ["a2", "w3"], ["m3"])
add3 = helper.make_node("Add", ["m3", "b3"], ["output"])

# -------------------------
# GRAPH
# -------------------------

graph = helper.make_graph(
    [
        matmul1, add1, relu1,
        matmul2, add2, relu2,
        matmul3, add3
    ],
    "JudgeNN",
    [input_tensor],
    [output_tensor],
    [init_w1, init_b1, init_w2, init_b2, init_w3, init_b3],
)

# -------------------------
# MODEL
# -------------------------

model_onnx = helper.make_model(
    graph,
    opset_imports=[helper.make_opsetid("", 13)]
)

onnx.save(model_onnx, "model.onnx")

print("EZKL-compatible ONNX model generated: model.onnx")
"""Shared fixtures for the mclust plot proofs. The same formulas are in plot_record.R."""

import numpy as np


def make_fixtures():
    i = np.arange(1, 61, dtype=float)
    g3 = (i - 1) % 3
    x1 = 1.3 * np.cos(0.37 * i) + 2.5 * g3
    x2 = 0.9 * np.sin(0.53 * i) + 0.8 * g3 - 0.5
    x3 = 0.4 * np.cos(0.9 * i) + 0.2 * np.sin(1.7 * i)
    data3 = np.column_stack([x1, x2, x3])
    data2 = data3[:, :2].copy()
    cls = (((i * 7) % 3) + 1).astype(float)
    truth = cls.copy()
    idx = np.array([5, 17, 33, 48]) - 1
    truth[idx] = (truth[idx] % 3) + 1
    mu2 = np.array([[0.2, 2.4, 1.1], [-0.1, 0.6, 2.2]])
    S1 = np.array([[1.2, 0.4], [0.4, 0.8]])
    S2 = np.array([[0.6, -0.2], [-0.2, 1.1]])
    S3 = np.array([[0.9, 0.0], [0.0, 0.5]])
    sig2 = np.zeros((2, 2, 3))
    sig2[:, :, 0], sig2[:, :, 1], sig2[:, :, 2] = S1, S2, S3
    pro = np.array([0.3, 0.4, 0.3])
    w = np.column_stack([
        np.exp(-0.5 * ((data2[:, 0] - mu2[0, k]) ** 2 + (data2[:, 1] - mu2[1, k]) ** 2)) + 1e-3
        for k in range(3)
    ])
    z = w / w.sum(axis=1, keepdims=True)
    mu3 = np.array([[0.2, 2.4, 1.1], [-0.1, 0.6, 2.2], [0.3, -0.4, 0.5]])
    A1 = np.array([[1.0, 0.3, 0.0], [0.2, 0.9, 0.2], [0.0, 0.1, 0.7]])
    A2 = np.array([[0.8, 0.1, 0.2], [0.0, 1.1, 0.4], [0.3, 0.0, 0.6]])
    A3 = np.array([[0.7, 0.0, 0.2], [0.1, 0.9, 0.0], [0.1, 0.3, 1.0]])
    sig3 = np.zeros((3, 3, 3))
    for k, A in enumerate([A1, A2, A3]):
        sig3[:, :, k] = A @ A.T + 0.3 * np.eye(3)
    return {
        "data3": data3, "data2": data2, "cls": cls, "truth": truth,
        "mu2": mu2, "sig2": sig2, "pro": pro, "z": z,
        "mu3": mu3, "sig3": sig3,
    }

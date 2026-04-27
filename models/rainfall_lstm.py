"""
MODULE — LSTM Rainfall Prediction Model (PyTorch)
Predicts rainfall for next 24h / 48h / 72h using 7-day weather sequence.
"""

import sys
sys.path.insert(0, '.')

import os
import numpy as np
import torch
import torch.nn as nn
from utils.logger import get_logger

logger = get_logger("rainfall_lstm")

# ── Model save path ───────────────────────────────────────────
MODEL_DIR  = os.path.join(os.path.dirname(__file__), "saved")
MODEL_PATH = os.path.join(MODEL_DIR, "rainfall_lstm.pt")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.npz")
os.makedirs(MODEL_DIR, exist_ok=True)

# ── Hyperparameters ───────────────────────────────────────────
INPUT_SIZE  = 5    # features: temp, humidity, pressure, rainfall, wind
HIDDEN_SIZE = 64
NUM_LAYERS  = 2
OUTPUT_SIZE = 3    # predictions: 24h, 48h, 72h rainfall
DROPOUT     = 0.2
SEQUENCE_LEN = 7   # 7 days of input


# ── LSTM Model ────────────────────────────────────────────────
class RainfallLSTM(nn.Module):
    def __init__(self):
        super(RainfallLSTM, self).__init__()

        self.lstm = nn.LSTM(
            input_size=INPUT_SIZE,
            hidden_size=HIDDEN_SIZE,
            num_layers=NUM_LAYERS,
            dropout=DROPOUT,
            batch_first=True
        )

        self.fc = nn.Sequential(
            nn.Linear(HIDDEN_SIZE, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, OUTPUT_SIZE),
            nn.ReLU()  # rainfall can't be negative
        )

    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        lstm_out, _ = self.lstm(x)
        # Take last timestep output
        last_out = lstm_out[:, -1, :]
        out = self.fc(last_out)
        return out


# ── Scaler ────────────────────────────────────────────────────
class MinMaxScaler:
    """Simple min-max scaler saved alongside model."""
    def __init__(self):
        self.min_vals = None
        self.max_vals = None

    def fit(self, X: np.ndarray):
        self.min_vals = X.min(axis=(0, 1), keepdims=True)
        self.max_vals = X.max(axis=(0, 1), keepdims=True)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        range_vals = np.where(
            self.max_vals - self.min_vals == 0,
            1,
            self.max_vals - self.min_vals
        )
        return (X - self.min_vals) / range_vals

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def save(self, path: str):
        np.savez(path, min_vals=self.min_vals, max_vals=self.max_vals)

    def load(self, path: str):
        data = np.load(path)
        self.min_vals = data["min_vals"]
        self.max_vals = data["max_vals"]
        return self


# ── Load trained model ────────────────────────────────────────
_model  = None
_scaler = None

def load_model():
    """Load trained LSTM model and scaler from disk."""
    global _model, _scaler

    if _model is not None:
        return _model, _scaler

    if not os.path.exists(MODEL_PATH):
        logger.warning("LSTM model not found — run model_trainer.py first")
        return None, None

    if not os.path.exists(SCALER_PATH + ".npz"):
        logger.warning("Scaler not found — run model_trainer.py first")
        return None, None

    try:
        _model = RainfallLSTM()
        _model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu", weights_only=True))
        _model.eval()

        _scaler = MinMaxScaler().load(SCALER_PATH + ".npz")

        logger.info("LSTM model loaded successfully")
        return _model, _scaler

    except Exception as e:
        logger.error(f"Error loading LSTM model: {e}")
        return None, None


# ── Predict rainfall ─────────────────────────────────────────
def predict_rainfall(past_7_days: list) -> dict:
    """
    Predict rainfall for next 24h / 48h / 72h.

    Input: list of 7 dicts with keys: temp, humidity, pressure, rainfall, wind
    Output: {
        "rainfall_mm_24h": float,
        "rainfall_mm_48h": float,
        "rainfall_mm_72h": float,
        "probability_24h": float (0-1),
        "probability_48h": float (0-1),
        "probability_72h": float (0-1),
        "source": "lstm" or "fallback"
    }
    """
    model, scaler = load_model()

    if model is None or scaler is None:
        return _fallback_prediction(past_7_days)

    try:
        # Convert to numpy array
        arr = np.array([[
            d.get("temp",     28.0),
            d.get("humidity", 65.0),
            d.get("pressure", 101.3),
            d.get("rainfall", 0.0),
            d.get("wind",     2.5),
        ] for d in past_7_days], dtype=np.float32)

        # Scale
        arr_scaled = scaler.transform(arr.reshape(1, 7, 5)).reshape(1, 7, 5)

        # Predict
        tensor = torch.FloatTensor(arr_scaled)
        with torch.no_grad():
            output = model(tensor).numpy()[0]

        rain_24h = max(0.0, float(output[0]))
        rain_48h = max(0.0, float(output[1]))
        rain_72h = max(0.0, float(output[2]))

        # Convert mm to probability (sigmoid-like)
        prob_24h = min(1.0, rain_24h / 50.0)
        prob_48h = min(1.0, rain_48h / 50.0)
        prob_72h = min(1.0, rain_72h / 50.0)

        result = {
            "rainfall_mm_24h": round(rain_24h, 2),
            "rainfall_mm_48h": round(rain_48h, 2),
            "rainfall_mm_72h": round(rain_72h, 2),
            "probability_24h": round(prob_24h, 2),
            "probability_48h": round(prob_48h, 2),
            "probability_72h": round(prob_72h, 2),
            "source": "lstm"
        }

        logger.info(f"LSTM prediction: 24h={rain_24h:.1f}mm, 48h={rain_48h:.1f}mm, 72h={rain_72h:.1f}mm")
        return result

    except Exception as e:
        logger.error(f"LSTM prediction error: {e}")
        return _fallback_prediction(past_7_days)


def _fallback_prediction(past_7_days: list) -> dict:
    """
    Rule-based fallback when LSTM model not available.
    Uses recent rainfall trend to estimate next days.
    """
    recent_rain = [d.get("rainfall", 0.0) for d in past_7_days]
    avg_rain = sum(recent_rain) / len(recent_rain) if recent_rain else 0.0
    trend = recent_rain[-1] - recent_rain[0] if len(recent_rain) >= 2 else 0.0

    rain_24h = max(0.0, avg_rain + trend * 0.3)
    rain_48h = max(0.0, avg_rain + trend * 0.5)
    rain_72h = max(0.0, avg_rain + trend * 0.7)

    return {
        "rainfall_mm_24h": round(rain_24h, 2),
        "rainfall_mm_48h": round(rain_48h, 2),
        "rainfall_mm_72h": round(rain_72h, 2),
        "probability_24h": round(min(1.0, rain_24h / 50.0), 2),
        "probability_48h": round(min(1.0, rain_48h / 50.0), 2),
        "probability_72h": round(min(1.0, rain_72h / 50.0), 2),
        "source": "fallback"
    }


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing LSTM model structure...")

    model = RainfallLSTM()
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Test with dummy data
    dummy = torch.randn(1, SEQUENCE_LEN, INPUT_SIZE)
    output = model(dummy)
    print(f"Input shape:  {dummy.shape}")
    print(f"Output shape: {output.shape}")
    print(f"Output (raw): {output.detach().numpy()}")

    # Test prediction with fallback
    dummy_7days = [
        {"temp": 30.0, "humidity": 70.0, "pressure": 101.3, "rainfall": 5.0, "wind": 3.0},
        {"temp": 31.0, "humidity": 72.0, "pressure": 101.1, "rainfall": 8.0, "wind": 3.5},
        {"temp": 29.0, "humidity": 75.0, "pressure": 100.8, "rainfall": 12.0, "wind": 4.0},
        {"temp": 28.0, "humidity": 78.0, "pressure": 100.5, "rainfall": 15.0, "wind": 4.5},
        {"temp": 27.0, "humidity": 80.0, "pressure": 100.2, "rainfall": 10.0, "wind": 5.0},
        {"temp": 26.0, "humidity": 82.0, "pressure": 100.0, "rainfall": 6.0,  "wind": 4.0},
        {"temp": 25.0, "humidity": 85.0, "pressure": 99.8,  "rainfall": 3.0,  "wind": 3.5},
    ]

    result = predict_rainfall(dummy_7days)
    print(f"\nFallback prediction (no trained model yet):")
    for k, v in result.items():
        print(f"  {k}: {v}")

    print("\nLSTM module ready! Run model_trainer.py to train.")
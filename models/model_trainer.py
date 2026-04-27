"""
MODULE — LSTM Model Trainer
Fetches NASA POWER data for 20 districts, trains LSTM, saves model.
Run once: python models/model_trainer.py
Training time: ~10-15 minutes on CPU
"""

import sys
sys.path.insert(0, '.')

import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau

from ingestion.nasa_power import fetch_all_districts
from ingestion.data_normalizer import normalize_nasa_power, df_to_sequences
from models.rainfall_lstm import RainfallLSTM, MinMaxScaler, MODEL_PATH, SCALER_PATH
from utils.logger import get_logger

logger = get_logger("model_trainer")

# ── Training config ───────────────────────────────────────────
EPOCHS      = 50
BATCH_SIZE  = 32
LR          = 0.001
WINDOW      = 7       # 7 days input
TRAIN_SPLIT = 0.8
PATIENCE    = 10      # early stopping patience


def prepare_training_data(start_year: int = 2014, end_year: int = 2024):
    """
    Fetch data from all districts and combine into one big dataset.
    Returns: X (n, 7, 5), y (n, 3)
    """
    logger.info("Fetching NASA POWER data for all districts...")
    all_data = fetch_all_districts(start_year=start_year, end_year=end_year)

    if not all_data:
        logger.error("No data fetched! Check internet connection.")
        return None, None

    all_X, all_y = [], []

    for district, df in all_data.items():
        df_clean = normalize_nasa_power(df)

        if df_clean.empty or len(df_clean) < WINDOW + 3:
            logger.warning(f"Skipping {district} — not enough data")
            continue

        X, y_1d = df_to_sequences(df_clean, window=WINDOW)

        if len(X) == 0:
            continue

        # Build 3-day targets: [24h, 48h, 72h] rainfall
        features = df_clean["rainfall_mm"].values
        y_3d = []
        for i in range(len(features) - WINDOW - 2):
            y_3d.append([
                features[i + WINDOW],
                features[i + WINDOW + 1],
                features[i + WINDOW + 2],
            ])

        y_3d = np.array(y_3d, dtype=np.float32)
        min_len = min(len(X), len(y_3d))
        X = X[:min_len]
        y_3d = y_3d[:min_len]

        all_X.append(X)
        all_y.append(y_3d)
        logger.info(f"  {district}: {len(X)} sequences added")

    if not all_X:
        logger.error("No sequences created!")
        return None, None

    X_all = np.concatenate(all_X, axis=0)
    y_all = np.concatenate(all_y, axis=0)

    logger.info(f"Total dataset: X={X_all.shape}, y={y_all.shape}")
    return X_all, y_all


def train():
    """Main training function."""
    logger.info("=" * 50)
    logger.info("KisanMitra LSTM Training Started")
    logger.info("=" * 50)

    # ── Step 1: Load data ─────────────────────────────────────
    X, y = prepare_training_data(start_year=2016, end_year=2024)

    if X is None:
        logger.error("Training aborted — no data")
        return

    # ── Step 2: Scale features ────────────────────────────────
    logger.info("Scaling features...")
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    # Scale y (rainfall targets) — clip to max 200mm
    y = np.clip(y, 0, 200) / 200.0

    # ── Step 3: Train/val split ───────────────────────────────
    n = len(X_scaled)
    split = int(n * TRAIN_SPLIT)

    # Shuffle before split
    idx = np.random.permutation(n)
    X_scaled = X_scaled[idx]
    y = y[idx]

    X_train = X_scaled[:split]
    X_val   = X_scaled[split:]
    y_train = y[:split]
    y_val   = y[split:]

    logger.info(f"Train: {len(X_train)} | Val: {len(X_val)}")

    # ── Step 4: Create DataLoaders ────────────────────────────
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train),
        torch.FloatTensor(y_train)
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X_val),
        torch.FloatTensor(y_val)
    )

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)

    # ── Step 5: Model, optimizer, loss ───────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training on: {device}")

    model     = RainfallLSTM().to(device)
    optimizer = Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()
    scheduler = ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # ── Step 6: Training loop ─────────────────────────────────
    best_val_loss  = float("inf")
    patience_count = 0
    best_state     = None

    logger.info(f"Training for {EPOCHS} epochs...")
    print()

    for epoch in range(1, EPOCHS + 1):
        # Train
        model.train()
        train_losses = []

        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad()
            output = model(X_batch)
            loss   = criterion(output, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(loss.item())

        # Validate
        model.eval()
        val_losses = []

        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)
                output  = model(X_batch)
                loss    = criterion(output, y_batch)
                val_losses.append(loss.item())

        train_loss = np.mean(train_losses)
        val_loss   = np.mean(val_losses)
        scheduler.step(val_loss)

        # Progress print every 5 epochs
        if epoch % 5 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{EPOCHS} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}")

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss  = val_loss
            patience_count = 0
            best_state     = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            patience_count += 1
            if patience_count >= PATIENCE:
                logger.info(f"Early stopping at epoch {epoch}")
                break

    # ── Step 7: Save model ────────────────────────────────────
    print()
    logger.info("Saving model...")

    if best_state:
        model.load_state_dict(best_state)

    torch.save(model.state_dict(), MODEL_PATH)
    scaler.save(SCALER_PATH)

    logger.info(f"Model saved: {MODEL_PATH}")
    logger.info(f"Scaler saved: {SCALER_PATH}.npz")
    logger.info(f"Best val loss: {best_val_loss:.6f}")

    # ── Step 8: Quick test ────────────────────────────────────
    logger.info("Testing trained model...")
    model.eval()

    sample_X = torch.FloatTensor(X_val[:1]).to(device)
    with torch.no_grad():
        pred = model(sample_X).cpu().numpy()[0]

    pred_mm = pred * 200.0  # unscale
    true_mm = y_val[0] * 200.0

    print(f"\nSample prediction:")
    print(f"  Predicted: 24h={pred_mm[0]:.1f}mm, 48h={pred_mm[1]:.1f}mm, 72h={pred_mm[2]:.1f}mm")
    print(f"  Actual:    24h={true_mm[0]:.1f}mm, 48h={true_mm[1]:.1f}mm, 72h={true_mm[2]:.1f}mm")

    logger.info("=" * 50)
    logger.info("Training Complete!")
    logger.info("=" * 50)
    print("\nModel ready! You can now use predict_rainfall() in rainfall_lstm.py")


if __name__ == "__main__":
    train()
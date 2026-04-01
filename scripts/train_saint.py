"""
Entraînement SAINT+ pour Knowledge Tracing.

Le modèle utilise l'architecture Transformer (Encoder-Decoder) :
- Encoder : traite la séquence d'exercices (ID exercice + ID compétence)
- Decoder : traite la séquence de réponses (correct/incorrect + temps)
- Cross-attention : le décodeur attend les informations de l'encodeur

Usage :
  python scripts/train_saint.py --mode small --epochs 50
  python scripts/train_saint.py --mode full --epochs 100
"""

import os
import json
import argparse
import time
import math

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import roc_auc_score, accuracy_score


# ═══════════════════════════════════════════════════
# 1. CONFIGURATION
# ═══════════════════════════════════════════════════

CONFIGS = {
    "small": {
        "max_seq_len": 20,
        "d_model": 32,
        "n_heads": 4,
        "n_blocks": 2,
        "dropout": 0.1,
        "batch_size": 2,
        "lr": 0.001,
        "epochs": 50,
    },
    "full": {
        "max_seq_len": 200,
        "d_model": 64,
        "n_heads": 8,
        "n_blocks": 4,
        "dropout": 0.1,
        "batch_size": 32,
        "lr": 0.001,
        "epochs": 100,
    }
}


# ═══════════════════════════════════════════════════
# 2. DATASET
# ═══════════════════════════════════════════════════

class KTDataset(Dataset):
    """
    Dataset pour Knowledge Tracing.
    
    Charge les interactions depuis un CSV, groupe par utilisateur,
    et retourne des séquences paddées/tronquées.
    """

    def __init__(self, csv_path, max_seq_len=200):
        self.max_seq_len = max_seq_len
        self.sequences = []

        df = pd.read_csv(csv_path)

        for uid, group in df.groupby("uid"):
            group = group.sort_values("timestamps")

            questions = group["questions"].values
            concepts = group["concepts"].values
            responses = group["responses"].values
            timestamps = group["timestamps"].values
            elapsed = group["elapsed_time"].values if "elapsed_time" in group.columns \
                else np.zeros(len(group))

            # Découper en fenêtres si séquence trop longue
            n = len(questions)
            for start in range(0, n, max_seq_len):
                end = min(start + max_seq_len, n)
                if end - start < 3:  # Ignorer les séquences trop courtes
                    continue

                self.sequences.append({
                    "questions": questions[start:end],
                    "concepts": concepts[start:end],
                    "responses": responses[start:end],
                    "timestamps": timestamps[start:end],
                    "elapsed_time": elapsed[start:end],
                })

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        seq = self.sequences[idx]
        n = len(seq["questions"])

        # Tenseurs paddés
        questions = np.zeros(self.max_seq_len, dtype=np.int64)
        concepts = np.zeros(self.max_seq_len, dtype=np.int64)
        responses = np.zeros(self.max_seq_len, dtype=np.int64)
        elapsed = np.zeros(self.max_seq_len, dtype=np.float32)
        lag = np.zeros(self.max_seq_len, dtype=np.float32)
        mask = np.zeros(self.max_seq_len, dtype=np.float32)

        # Remplir (+1 pour réserver 0 au padding)
        questions[:n] = seq["questions"] + 1
        concepts[:n] = seq["concepts"] + 1
        responses[:n] = seq["responses"]
        mask[:n] = 1.0

        # Normaliser elapsed_time (log-scale)
        elapsed[:n] = np.log1p(seq["elapsed_time"]) / 7.0

        # Calculer lag_time (temps entre 2 interactions)
        if n > 1:
            ts = seq["timestamps"]
            lag_raw = np.zeros(n)
            lag_raw[1:] = np.diff(ts)
            lag[:n] = np.log1p(np.clip(lag_raw, 0, 1e8)) / 12.0

        return {
            "questions": torch.LongTensor(questions),
            "concepts": torch.LongTensor(concepts),
            "responses": torch.LongTensor(responses),
            "elapsed_time": torch.FloatTensor(elapsed),
            "lag_time": torch.FloatTensor(lag),
            "mask": torch.FloatTensor(mask),
        }


# ═══════════════════════════════════════════════════
# 3. MODÈLE SAINT+
# ═══════════════════════════════════════════════════

class SAINTPlus(nn.Module):
    """
    SAINT+ : Self-Attentive model for knowledge tracing
    (Shin et al., 2021)

    Encoder : traite les exercices (exercise_id + skill_id)
    Decoder : traite les réponses (response + elapsed_time + lag_time)
    Sortie  : P(correct) pour chaque position temporelle
    """

    def __init__(self, n_exercises, n_skills, d_model=64,
                 n_heads=8, n_blocks=4, dropout=0.1, max_seq_len=200):
        super().__init__()

        self.d_model = d_model

        # ── Encoder embeddings (côté exercice) ──
        self.exercise_emb = nn.Embedding(n_exercises + 1, d_model, padding_idx=0)
        self.skill_emb = nn.Embedding(n_skills + 1, d_model, padding_idx=0)

        # ── Decoder embeddings (côté réponse) ──
        # 0 = incorrect, 1 = correct, 2 = start token (pas de réponse précédente)
        self.response_emb = nn.Embedding(3, d_model)

        # ── SAINT+ : features temporelles ──
        self.elapsed_linear = nn.Linear(1, d_model)
        self.lag_linear = nn.Linear(1, d_model)

        # ── Position ──
        self.pos_emb = nn.Embedding(max_seq_len, d_model)

        # ── Transformer Encoder ──
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
            norm_first=True
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=n_blocks)

        # ── Transformer Decoder ──
        dec_layer = nn.TransformerDecoderLayer(
            d_model=d_model, nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
            norm_first=True
        )
        self.decoder = nn.TransformerDecoder(dec_layer, num_layers=n_blocks)

        # ── Sortie ──
        self.fc_out = nn.Linear(d_model, 1)
        self.dropout_layer = nn.Dropout(dropout)

    def forward(self, exercises, skills, responses,
                elapsed_time=None, lag_time=None, mask=None):
        """
        Forward pass.

        Args:
            exercises:    (batch, seq_len) IDs exercices
            skills:       (batch, seq_len) IDs compétences
            responses:    (batch, seq_len) 0 ou 1
            elapsed_time: (batch, seq_len) temps normalisé
            lag_time:     (batch, seq_len) lag normalisé
            mask:         (batch, seq_len) 1=valide, 0=padding

        Returns:
            (batch, seq_len) P(correct) entre 0 et 1
        """
        batch_size, seq_len = exercises.size()
        device = exercises.device

        # Positions
        pos = torch.arange(seq_len, device=device).unsqueeze(0)
        pos = pos.expand(batch_size, -1)

        # ── ENCODER : exercice + compétence + position ──
        enc_in = (self.exercise_emb(exercises) +
                  self.skill_emb(skills) +
                  self.pos_emb(pos))
        enc_in = self.dropout_layer(enc_in)

        # ── DECODER : réponse décalée + temps + position ──
        # Décalage : réponse[t-1] pour prédire au temps t
        shifted = torch.full_like(responses, 2)  # 2 = start token
        shifted[:, 1:] = responses[:, :-1]

        dec_in = self.response_emb(shifted) + self.pos_emb(pos)

        if elapsed_time is not None:
            dec_in = dec_in + self.elapsed_linear(elapsed_time.unsqueeze(-1))
        if lag_time is not None:
            dec_in = dec_in + self.lag_linear(lag_time.unsqueeze(-1))

        dec_in = self.dropout_layer(dec_in)

        # ── Masks ──
        # Padding mask : True là où il faut IGNORER
        padding_mask = None
        if mask is not None:
            padding_mask = (mask == 0)

        # Masque causal : le décodeur ne voit que le passé
        causal_mask = torch.triu(
            torch.ones(seq_len, seq_len, device=device), diagonal=1
        ).bool()

        # ── Transformer ──
        enc_out = self.encoder(enc_in, src_key_padding_mask=padding_mask)

        dec_out = self.decoder(
            dec_in, enc_out,
            tgt_mask=causal_mask,
            tgt_key_padding_mask=padding_mask,
            memory_key_padding_mask=padding_mask
        )

        # ── Sortie ──
        output = self.fc_out(dec_out).squeeze(-1)
        output = torch.sigmoid(output)

        return output


# ═══════════════════════════════════════════════════
# 4. ENTRAÎNEMENT
# ═══════════════════════════════════════════════════

def train_one_epoch(model, dataloader, optimizer, device):
    """Entraîne le modèle pendant une epoch."""
    model.train()
    total_loss = 0
    total_count = 0

    for batch in dataloader:
        # Déplacer vers le device
        q = batch["questions"].to(device)
        c = batch["concepts"].to(device)
        r = batch["responses"].to(device)
        et = batch["elapsed_time"].to(device)
        lt = batch["lag_time"].to(device)
        m = batch["mask"].to(device)

        # Forward
        predictions = model(q, c, r, et, lt, m)

        # Loss (BCE seulement sur les positions valides)
        loss = F.binary_cross_entropy(
            predictions, r.float(), reduction="none"
        )
        loss = (loss * m).sum() / m.sum()

        # Backward
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        total_loss += loss.item() * m.sum().item()
        total_count += m.sum().item()

    return total_loss / total_count if total_count > 0 else 0


def evaluate(model, dataloader, device):
    """Évalue le modèle (AUC + Accuracy)."""
    model.eval()
    all_preds = []
    all_targets = []
    total_loss = 0
    total_count = 0

    with torch.no_grad():
        for batch in dataloader:
            q = batch["questions"].to(device)
            c = batch["concepts"].to(device)
            r = batch["responses"].to(device)
            et = batch["elapsed_time"].to(device)
            lt = batch["lag_time"].to(device)
            m = batch["mask"].to(device)

            predictions = model(q, c, r, et, lt, m)

            loss = F.binary_cross_entropy(
                predictions, r.float(), reduction="none"
            )
            loss = (loss * m).sum() / m.sum()
            total_loss += loss.item() * m.sum().item()
            total_count += m.sum().item()

            # Collecter les prédictions valides
            valid = m.flatten().bool()
            preds = predictions.flatten()[valid].cpu().numpy()
            targets = r.flatten()[valid].cpu().numpy()

            all_preds.extend(preds)
            all_targets.extend(targets)

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    if len(all_targets) == 0:
        return {
            "loss": 0.0,
            "auc": 0.5,
            "accuracy": 0.5,
        }

    avg_loss = total_loss / total_count if total_count > 0 else 0

    # AUC
    try:
        auc = roc_auc_score(all_targets, all_preds)
    except ValueError:
        auc = 0.5

    # Accuracy
    acc = accuracy_score(all_targets, (all_preds >= 0.5).astype(int))

    return {
        "loss": round(avg_loss, 4),
        "auc": round(auc, 4),
        "accuracy": round(acc, 4),
    }


# ═══════════════════════════════════════════════════
# 5. MAIN
# ═══════════════════════════════════════════════════

def main(mode="full", epochs=None):
    """Point d'entrée principal."""

    print("\n" + "=" * 60)
    print("🧠 ENTRAÎNEMENT SAINT+ — Knowledge Tracing")
    print("=" * 60)

    # ── Config ──
    config = CONFIGS[mode].copy()
    if epochs is not None:
        config["epochs"] = epochs

    print(f"\n📋 Configuration ({mode}) :")
    for k, v in config.items():
        print(f"   {k:>15} = {v}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n   Device : {device}")

    # ── Charger les données ──
    data_dir = f"data/{mode}/prepared"
    info_path = f"{data_dir}/data_info.json"

    if not os.path.exists(info_path):
        print(f"\n❌ Données non préparées. Lancez d'abord :")
        print(f"   python scripts/prepare_data_pykt.py --mode {mode}")
        return

    with open(info_path) as f:
        data_info = json.load(f)

    print(f"\n📊 Données :")
    print(f"   Train : {data_info['n_train_interactions']} interactions")
    print(f"   Val   : {data_info['n_val_interactions']} interactions")
    print(f"   Test  : {data_info['n_test_interactions']} interactions")

    # ── Datasets ──
    max_seq = config["max_seq_len"]
    train_ds = KTDataset(f"{data_dir}/train.csv", max_seq)
    val_ds = KTDataset(f"{data_dir}/val.csv", max_seq)
    test_ds = KTDataset(f"{data_dir}/test.csv", max_seq)

    print(f"\n   Séquences train : {len(train_ds)}")
    print(f"   Séquences val   : {len(val_ds)}")
    print(f"   Séquences test  : {len(test_ds)}")

    # ── DataLoaders ──
    train_dl = DataLoader(train_ds, batch_size=config["batch_size"],
                          shuffle=True, drop_last=False)
    val_dl = DataLoader(val_ds, batch_size=config["batch_size"],
                        shuffle=False)
    test_dl = DataLoader(test_ds, batch_size=config["batch_size"],
                         shuffle=False)

    # ── Modèle ──
    n_ex = data_info["n_exercises"]
    n_sk = data_info["n_skills"]

    model = SAINTPlus(
        n_exercises=n_ex,
        n_skills=n_sk,
        d_model=config["d_model"],
        n_heads=config["n_heads"],
        n_blocks=config["n_blocks"],
        dropout=config["dropout"],
        max_seq_len=max_seq
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n🏗️  Modèle SAINT+ :")
    print(f"   Exercices    : {n_ex}")
    print(f"   Compétences  : {n_sk}")
    print(f"   d_model      : {config['d_model']}")
    print(f"   Attention    : {config['n_heads']} têtes × {config['n_blocks']} blocs")
    print(f"   Paramètres   : {n_params:,}")

    # ── Optimizer + Scheduler ──
    optimizer = torch.optim.Adam(model.parameters(), lr=config["lr"])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=10
    )

    # ── Entraînement ──
    print(f"\n🚀 Entraînement ({config['epochs']} epochs)")
    print(f"   {'Epoch':>6} {'Train Loss':>12} {'Val Loss':>10} "
          f"{'Val AUC':>9} {'Val Acc':>9} {'Temps':>7}")
    print(f"   {'─' * 6} {'─' * 12} {'─' * 10} {'─' * 9} {'─' * 9} {'─' * 7}")

    best_auc = 0
    best_epoch = 0
    patience_counter = 0
    patience_limit = 20
    history = []

    for epoch in range(1, config["epochs"] + 1):
        t0 = time.time()

        # Train
        train_loss = train_one_epoch(model, train_dl, optimizer, device)

        # Validate
        if len(val_ds) > 0:
            val_metrics = evaluate(model, val_dl, device)
        else:
            val_metrics = {"loss": 0.0, "auc": 0.5, "accuracy": 0.5}

        elapsed = time.time() - t0

        # Log
        print(f"   {epoch:>6} {train_loss:>12.4f} {val_metrics['loss']:>10.4f} "
              f"{val_metrics['auc']:>9.4f} {val_metrics['accuracy']:>9.4f} "
              f"{elapsed:>6.1f}s", end="")

        # Scheduler
        scheduler.step(val_metrics["auc"])

        # Best model
        if val_metrics["auc"] > best_auc:
            best_auc = val_metrics["auc"]
            best_epoch = epoch
            patience_counter = 0

            # Sauvegarder
            save_dir = f"models/saint_{mode}"
            os.makedirs(save_dir, exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "config": config,
                "data_info": data_info,
                "epoch": epoch,
                "best_auc": best_auc,
            }, f"{save_dir}/best_model.pt")

            print(" ★ best", end="")
        else:
            patience_counter += 1

        print()

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_metrics["loss"],
            "val_auc": val_metrics["auc"],
            "val_accuracy": val_metrics["accuracy"],
        })

        # Early stopping
        if patience_counter >= patience_limit:
            print(f"\n   ⏹️  Early stopping à l'epoch {epoch}")
            break

    # ── Charger le meilleur modèle ──
    print(f"\n📦 Chargement du meilleur modèle (epoch {best_epoch})")
    save_dir = f"models/saint_{mode}"
    checkpoint = torch.load(f"{save_dir}/best_model.pt",
                            map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])

    # ── Évaluation finale sur Test ──
    print("\n" + "=" * 60)
    print("📊 ÉVALUATION FINALE (Test Set)")
    print("=" * 60)

    test_metrics = evaluate(model, test_dl, device)
    print(f"   Loss     : {test_metrics['loss']}")
    print(f"   AUC      : {test_metrics['auc']}")
    print(f"   Accuracy : {test_metrics['accuracy']}")

    # ── Sauvegarder l'historique ──
    results = {
        "config": config,
        "data_info": data_info,
        "best_epoch": best_epoch,
        "best_val_auc": best_auc,
        "test_metrics": test_metrics,
        "n_params": n_params,
        "history": history,
    }
    with open(f"{save_dir}/training_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # ── Résumé ──
    print(f"\n{'=' * 60}")
    print(f"✅ ENTRAÎNEMENT TERMINÉ")
    print(f"   Meilleur epoch   : {best_epoch}")
    print(f"   Meilleur val AUC : {best_auc}")
    print(f"   Test AUC         : {test_metrics['auc']}")
    print(f"   Test Accuracy    : {test_metrics['accuracy']}")
    print(f"   Modèle sauvé     : {save_dir}/best_model.pt")
    print(f"   Résultats        : {save_dir}/training_results.json")
    print(f"{'=' * 60}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement SAINT+")
    parser.add_argument("--mode", choices=["small", "full"], default="full")
    parser.add_argument("--epochs", type=int, default=None)
    args = parser.parse_args()

    main(mode=args.mode, epochs=args.epochs)
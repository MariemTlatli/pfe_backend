"""
Prépare les données pour l'entraînement SAINT+.

- Lit le CSV brut de l'étape 2
- Sépare train/val/test par utilisateurs (80/10/10)
- Sauvegarde les splits

Usage :
  python scripts/prepare_data_pykt.py --mode full
  python scripts/prepare_data_pykt.py --mode small
"""

import pandas as pd
import numpy as np
import json
import os
import argparse


def prepare(mode="full"):
    """Prépare les données avec split train/val/test."""

    print(f"\n📦 Préparation des données — mode '{mode}'")
    print("=" * 50)

    # ── 1. Lire le CSV brut ──
    csv_path = f"data/{mode}/interactions.csv"
    df = pd.read_csv(csv_path)
    print(f"  Lignes lues : {len(df)}")

    # ── 2. Statistiques ──
    n_users = df["uid"].nunique()
    n_exercises = df["questions"].nunique()
    n_skills = df["concepts"].nunique()
    print(f"  Utilisateurs : {n_users}")
    print(f"  Exercices    : {n_exercises}")
    print(f"  Compétences  : {n_skills}")

    # ── 3. Split par utilisateurs ──
    user_ids = sorted(df["uid"].unique())
    np.random.seed(42)
    np.random.shuffle(user_ids)

    n_train = int(len(user_ids) * 0.8)
    n_val = int(len(user_ids) * 0.1)

    train_users = set(user_ids[:n_train])
    val_users = set(user_ids[n_train:n_train + n_val])
    test_users = set(user_ids[n_train + n_val:])

    df_train = df[df["uid"].isin(train_users)]
    df_val = df[df["uid"].isin(val_users)]
    df_test = df[df["uid"].isin(test_users)]

    print(f"\n  Split :")
    print(f"    Train : {len(train_users)} users, {len(df_train)} interactions")
    print(f"    Val   : {len(val_users)} users, {len(df_val)} interactions")
    print(f"    Test  : {len(test_users)} users, {len(df_test)} interactions")

    # ── 4. Sauvegarder ──
    out_dir = f"data/{mode}/prepared"
    os.makedirs(out_dir, exist_ok=True)

    df_train.to_csv(f"{out_dir}/train.csv", index=False)
    df_val.to_csv(f"{out_dir}/val.csv", index=False)
    df_test.to_csv(f"{out_dir}/test.csv", index=False)

    # Sauvegarder les infos
    info = {
        "n_users": int(n_users),
        "n_exercises": int(n_exercises),
        "n_skills": int(n_skills),
        "n_train_users": len(train_users),
        "n_val_users": len(val_users),
        "n_test_users": len(test_users),
        "n_train_interactions": len(df_train),
        "n_val_interactions": len(df_val),
        "n_test_interactions": len(df_test),
    }
    with open(f"{out_dir}/data_info.json", "w") as f:
        json.dump(info, f, indent=2)

    print(f"\n  ✅ Fichiers sauvegardés dans {out_dir}/")
    print(f"     train.csv, val.csv, test.csv, data_info.json")
    print("=" * 50)

    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["small", "full"], default="full")
    args = parser.parse_args()
    prepare(args.mode)
# scripts/verify_dataset.py
"""Vérifie que les fichiers générés sont corrects."""

import csv
import json
import os


def verify(mode="small"):
    base = f"data/{mode}"
    print(f"\n🔍 Vérification du dataset '{mode}'")
    print("=" * 50)
    
    # 1. Vérifier le CSV
    csv_path = f"{base}/interactions.csv"
    assert os.path.exists(csv_path), f"❌ {csv_path} manquant"
    
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"  CSV : {len(rows)} lignes")
    
    # Vérifier les colonnes
    required = {"uid", "questions", "concepts", "responses",
                "selectmasks", "timestamps"}
    assert required.issubset(set(rows[0].keys())), \
        f"❌ Colonnes manquantes: {required - set(rows[0].keys())}"
    print(f"  Colonnes : ✅ {', '.join(sorted(rows[0].keys()))}")
    
    # Vérifier les valeurs
    uids = set(r["uid"] for r in rows)
    concepts = set(r["concepts"] for r in rows)
    responses = set(r["responses"] for r in rows)
    
    print(f"  Étudiants uniques  : {len(uids)}")
    print(f"  Compétences uniques: {len(concepts)}")
    assert responses == {"0", "1"}, f"❌ Responses invalides: {responses}"
    print(f"  Responses          : ✅ (0 et 1 uniquement)")
    
    # Taux de réussite
    correct = sum(1 for r in rows if r["responses"] == "1")
    rate = correct / len(rows)
    print(f"  Taux réussite      : {rate:.1%}")
    assert 0.3 < rate < 0.85, f"❌ Taux anormal: {rate:.1%}"
    print(f"  Distribution       : ✅ (entre 30% et 85%)")
    
    # 2. Vérifier le format pyKT
    pykt_path = f"{base}/pykt_format.txt"
    assert os.path.exists(pykt_path), f"❌ {pykt_path} manquant"
    
    with open(pykt_path) as f:
        lines = f.readlines()
    
    # Parcourir les séquences
    idx = 0
    n_students_pykt = 0
    total_interactions = 0
    while idx < len(lines):
        n = int(lines[idx].strip())
        total_interactions += n
        
        questions = lines[idx + 1].strip().split(",")
        concepts_ = lines[idx + 2].strip().split(",")
        responses_ = lines[idx + 3].strip().split(",")
        timestamps = lines[idx + 4].strip().split(",")
        
        assert len(questions) == n, f"❌ Ligne {idx+1}: attendu {n}, got {len(questions)}"
        assert len(concepts_) == n
        assert len(responses_) == n
        assert len(timestamps) == n
        
        n_students_pykt += 1
        idx += 5
    
    print(f"\n  pyKT format : ✅")
    print(f"  Étudiants pyKT     : {n_students_pykt}")
    print(f"  Interactions pyKT  : {total_interactions}")
    assert total_interactions == len(rows), "❌ Mismatch CSV vs pyKT"
    print(f"  Cohérence CSV/pyKT : ✅")
    
    # 3. Vérifier les métadonnées
    meta_path = f"{base}/metadata.json"
    with open(meta_path) as f:
        meta = json.load(f)
    
    print(f"\n  Métadonnées : ✅")
    print(f"  Config : {meta['config']['description']}")
    
    print(f"\n{'='*50}")
    print(f"✅ Dataset '{mode}' VALIDE !")
    print(f"{'='*50}")


if __name__ == "__main__":
    verify("small")
    verify("full")
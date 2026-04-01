"""
Tests de validation — Intégration SAINT+ complète.
Configuré pour MongoDB Atlas.

Usage :
  python tests/test_saint_integration.py
"""

import os
import sys
import json
import math
import time
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch


# ═══════════════════════════════════════════════
# Configuration MongoDB Atlas
# ═══════════════════════════════════════════════

MONGO_URI = "mongodb+srv://crud:H24ZJZXDzDOoVYKD@cluster0.gjtsy.mongodb.net/"


# ═══════════════════════════════════════════════
# Utilitaires de test
# ═══════════════════════════════════════════════

class TestRunner:
    def __init__(self):
        self.results = []
        self.current_section = ""

    def section(self, name):
        self.current_section = name
        print(f"\n{'='*60}")
        print(f"🧪 {name}")
        print(f"{'='*60}")

    def test(self, name, func):
        print(f"\n  ▶ {name}...", end=" ")
        try:
            result = func()
            if result is True or result is None:
                print("✅ OK")
                self.results.append(("PASS", self.current_section, name))
                return True
            else:
                print(f"❌ FAIL: {result}")
                self.results.append(("FAIL", self.current_section, name, str(result)))
                return False
        except Exception as e:
            print(f"💥 ERROR: {e}")
            traceback.print_exc()
            self.results.append(("ERROR", self.current_section, name, str(e)))
            return False

    def summary(self):
        print(f"\n{'='*60}")
        print(f"📊 RÉSUMÉ DES TESTS")
        print(f"{'='*60}")

        passed = sum(1 for r in self.results if r[0] == "PASS")
        failed = sum(1 for r in self.results if r[0] == "FAIL")
        errors = sum(1 for r in self.results if r[0] == "ERROR")
        total = len(self.results)

        print(f"\n  Total  : {total}")
        print(f"  ✅ Pass : {passed}")
        print(f"  ❌ Fail : {failed}")
        print(f"  💥 Error: {errors}")

        if failed + errors > 0:
            print(f"\n  Détails des échecs :")
            for r in self.results:
                if r[0] != "PASS":
                    print(f"    {r[0]} | {r[1]} | {r[2]}")
                    if len(r) > 3:
                        print(f"           → {r[3]}")

        print(f"\n  {'✅ TOUS LES TESTS PASSENT !' if failed + errors == 0 else '❌ CERTAINS TESTS ÉCHOUENT'}")
        print(f"{'='*60}")
        return failed + errors == 0


runner = TestRunner()


# ═══════════════════════════════════════════════
# TEST 1 : Chargement du modèle
# ═══════════════════════════════════════════════

runner.section("TEST 1 — Chargement du modèle SAINT+")


def test_model_file_exists():
    path = os.path.join("models", "saint_full", "best_model.pt")
    if not os.path.exists(path):
        return f"Fichier {path} introuvable"
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"({size_mb:.1f} MB)", end=" ")
    return True

runner.test("Fichier best_model.pt existe", test_model_file_exists)


def test_model_load():
    path = os.path.join("models", "saint_full", "best_model.pt")
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)

    required_keys = ["model_state_dict", "config", "data_info"]
    for key in required_keys:
        if key not in checkpoint:
            return f"Clé manquante: {key}"

    config = checkpoint["config"]
    data_info = checkpoint["data_info"]
    print(f"\n    Config: d_model={config['d_model']}, "
          f"n_heads={config['n_heads']}, n_blocks={config['n_blocks']}")
    print(f"    Data: {data_info['n_exercises']} exercices, "
          f"{data_info['n_skills']} compétences", end=" ")
    return True

runner.test("Checkpoint contient les bonnes clés", test_model_load)


def test_model_architecture():
    from scripts.train_saint import SAINTPlus

    path = os.path.join("models", "saint_full", "best_model.pt")
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)

    model = SAINTPlus(
        n_exercises=checkpoint["data_info"]["n_exercises"],
        n_skills=checkpoint["data_info"]["n_skills"],
        d_model=checkpoint["config"]["d_model"],
        n_heads=checkpoint["config"]["n_heads"],
        n_blocks=checkpoint["config"]["n_blocks"],
        dropout=0.0,
        max_seq_len=checkpoint["config"]["max_seq_len"]
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    n_params = sum(p.numel() for p in model.parameters())
    print(f"({n_params:,} paramètres)", end=" ")
    return True

runner.test("Architecture SAINT+ se charge", test_model_architecture)


def test_training_results():
    results_path = os.path.join("models", "saint_full", "training_results.json")
    if not os.path.exists(results_path):
        return f"Fichier {results_path} introuvable"

    with open(results_path) as f:
        results = json.load(f)

    test_auc = results["test_metrics"]["auc"]
    test_acc = results["test_metrics"]["accuracy"]
    print(f"(AUC={test_auc}, Acc={test_acc})", end=" ")

    if test_auc < 0.65:
        return f"AUC trop faible: {test_auc} (attendu > 0.65)"
    return True

runner.test("Résultats d'entraînement valides", test_training_results)


# ═══════════════════════════════════════════════
# TEST 2 : Prédiction synthétique
# ═══════════════════════════════════════════════

runner.section("TEST 2 — Prédiction sur séquence synthétique")


def test_forward_pass():
    from scripts.train_saint import SAINTPlus

    path = os.path.join("models", "saint_full", "best_model.pt")
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    config = checkpoint["config"]
    data_info = checkpoint["data_info"]

    model = SAINTPlus(
        n_exercises=data_info["n_exercises"],
        n_skills=data_info["n_skills"],
        d_model=config["d_model"],
        n_heads=config["n_heads"],
        n_blocks=config["n_blocks"],
        dropout=0.0,
        max_seq_len=config["max_seq_len"]
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    seq_len = 10
    max_seq = config["max_seq_len"]

    questions = torch.zeros(1, max_seq, dtype=torch.long)
    concepts = torch.zeros(1, max_seq, dtype=torch.long)
    responses = torch.zeros(1, max_seq, dtype=torch.long)
    elapsed = torch.zeros(1, max_seq)
    lag = torch.zeros(1, max_seq)
    mask = torch.zeros(1, max_seq)

    for i in range(seq_len):
        questions[0, i] = (i % data_info["n_exercises"]) + 1
        concepts[0, i] = (i % data_info["n_skills"]) + 1
        responses[0, i] = 1 if i % 3 != 0 else 0
        elapsed[0, i] = 0.5
        lag[0, i] = 0.3
        mask[0, i] = 1.0

    with torch.no_grad():
        output = model(questions, concepts, responses, elapsed, lag, mask)

    p = float(output[0, seq_len - 1])
    print(f"(P(correct)={p:.4f})", end=" ")

    if not (0.0 <= p <= 1.0):
        return f"P(correct) hors bornes: {p}"
    return True

runner.test("Forward pass avec données synthétiques", test_forward_pass)


def test_prediction_varies_with_performance():
    from scripts.train_saint import SAINTPlus

    path = os.path.join("models", "saint_full", "best_model.pt")
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    config = checkpoint["config"]
    data_info = checkpoint["data_info"]

    model = SAINTPlus(
        n_exercises=data_info["n_exercises"],
        n_skills=data_info["n_skills"],
        d_model=config["d_model"],
        n_heads=config["n_heads"],
        n_blocks=config["n_blocks"],
        dropout=0.0,
        max_seq_len=config["max_seq_len"]
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    max_seq = config["max_seq_len"]
    seq_len = 20

    def make_sequence(correct_rate):
        q = torch.zeros(1, max_seq, dtype=torch.long)
        c = torch.zeros(1, max_seq, dtype=torch.long)
        r = torch.zeros(1, max_seq, dtype=torch.long)
        e = torch.zeros(1, max_seq)
        l = torch.zeros(1, max_seq)
        m = torch.zeros(1, max_seq)

        for i in range(seq_len):
            q[0, i] = (i % data_info["n_exercises"]) + 1
            c[0, i] = 1
            r[0, i] = 1 if (i / seq_len) < correct_rate else 0
            e[0, i] = 0.5
            l[0, i] = 0.3
            m[0, i] = 1.0

        return q, c, r, e, l, m

    with torch.no_grad():
        good = model(*make_sequence(0.9))
    p_good = float(good[0, seq_len - 1])

    with torch.no_grad():
        bad = model(*make_sequence(0.2))
    p_bad = float(bad[0, seq_len - 1])

    print(f"(bon={p_good:.3f}, mauvais={p_bad:.3f})", end=" ")

    if p_good <= p_bad:
        return f"Le bon élève ({p_good:.3f}) devrait avoir un P plus élevé que le mauvais ({p_bad:.3f})"
    return True

runner.test("P(correct) bon élève > P(correct) mauvais élève", test_prediction_varies_with_performance)


def test_prediction_speed():
    from scripts.train_saint import SAINTPlus

    path = os.path.join("models", "saint_full", "best_model.pt")
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    config = checkpoint["config"]
    data_info = checkpoint["data_info"]

    model = SAINTPlus(
        n_exercises=data_info["n_exercises"],
        n_skills=data_info["n_skills"],
        d_model=config["d_model"],
        n_heads=config["n_heads"],
        n_blocks=config["n_blocks"],
        dropout=0.0,
        max_seq_len=config["max_seq_len"]
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    max_seq = config["max_seq_len"]
    q = torch.randint(0, data_info["n_exercises"], (1, max_seq))
    c = torch.randint(0, data_info["n_skills"], (1, max_seq))
    r = torch.randint(0, 2, (1, max_seq))
    e = torch.rand(1, max_seq)
    l = torch.rand(1, max_seq)
    m = torch.ones(1, max_seq)

    with torch.no_grad():
        model(q, c, r, e, l, m)

    n_runs = 20
    start = time.time()
    for _ in range(n_runs):
        with torch.no_grad():
            model(q, c, r, e, l, m)
    elapsed_time = (time.time() - start) / n_runs * 1000

    print(f"({elapsed_time:.1f}ms/inférence)", end=" ")

    if elapsed_time > 500:
        return f"Trop lent: {elapsed_time:.1f}ms (max 500ms)"
    return True

runner.test("Vitesse d'inférence < 500ms", test_prediction_speed)


# ═══════════════════════════════════════════════
# TEST 3 : Métriques enrichies
# ═══════════════════════════════════════════════

runner.section("TEST 3 — Métriques enrichies (post-traitement)")


def test_estimate_attempts():
    from app.services.saint_service import SAINTService

    r1 = SAINTService._estimate_attempts(0.9)
    assert r1["value"] <= 2, f"P=0.9 devrait donner 1-2 tentatives, got {r1['value']}"

    r2 = SAINTService._estimate_attempts(0.2)
    assert r2["value"] >= 4, f"P=0.2 devrait donner 4+ tentatives, got {r2['value']}"

    r3 = SAINTService._estimate_attempts(0.05)
    assert r3["value"] == 10, f"P=0.05 devrait donner 10 tentatives, got {r3['value']}"

    print(f"(P=0.9→{r1['value']}, P=0.2→{r2['value']}, P=0.05→{r3['value']})", end=" ")
    return True

runner.test("Tentatives estimées", test_estimate_attempts)


def test_hint_probability():
    from app.services.saint_service import SAINTService

    r1 = SAINTService._compute_hint_probability(0.8, [])
    assert r1["probability"] < 0.4, f"P=0.8 devrait avoir faible hint, got {r1['probability']}"

    raw = [
        {"is_correct": False, "time_spent": 60},
        {"is_correct": False, "time_spent": 80},
        {"is_correct": False, "time_spent": 90},
        {"is_correct": False, "time_spent": 70},
    ]
    r2 = SAINTService._compute_hint_probability(0.3, raw)
    assert r2["probability"] > 0.6, f"Série d'échecs devrait augmenter hint, got {r2['probability']}"

    print(f"(sans_echec={r1['level']}, avec_echecs={r2['level']})", end=" ")
    return True

runner.test("Probabilité de besoin d'indice", test_hint_probability)


def test_engagement():
    from app.services.saint_service import SAINTService

    now = datetime.utcnow()

    good_data = []
    for i in range(20):
        good_data.append({
            "is_correct": i % 3 != 0,
            "time_spent": 30 + i * 2,
            "created_at": now - timedelta(minutes=20 - i),
        })

    r1 = SAINTService._compute_engagement(good_data)
    assert r1["score"] > 0.5, f"Bon engagement devrait être > 0.5, got {r1['score']}"

    bad_data = []
    for i in range(20):
        bad_data.append({
            "is_correct": i % 2 == 0,
            "time_spent": 2,
            "created_at": now - timedelta(seconds=20 - i),
        })

    r2 = SAINTService._compute_engagement(bad_data)

    print(f"(bon={r1['score']:.2f}/{r1['level']}, "
          f"rush={r2['score']:.2f}/{r2['level']})", end=" ")
    return True

runner.test("Score d'engagement", test_engagement)


def test_anomaly_detection():
    from app.services.saint_service import SAINTService

    normal_data = [
        {"is_correct": True, "time_spent": 30, "exercise_id": "1",
         "created_at": datetime.utcnow() - timedelta(minutes=5)},
        {"is_correct": False, "time_spent": 45, "exercise_id": "2",
         "created_at": datetime.utcnow() - timedelta(minutes=3)},
        {"is_correct": True, "time_spent": 25, "exercise_id": "3",
         "created_at": datetime.utcnow()},
    ]
    r1 = SAINTService._detect_anomalies(0.6, normal_data)
    assert not r1["has_anomaly"], f"Normal devrait pas avoir d'anomalie"

    cheat_data = [
        {"is_correct": True, "time_spent": 30, "exercise_id": "1",
         "created_at": datetime.utcnow() - timedelta(minutes=2)},
        {"is_correct": True, "time_spent": 2, "exercise_id": "2",
         "created_at": datetime.utcnow() - timedelta(minutes=1)},
        {"is_correct": True, "time_spent": 1, "exercise_id": "3",
         "created_at": datetime.utcnow()},
    ]
    r2 = SAINTService._detect_anomalies(0.3, cheat_data)
    assert r2["has_anomaly"], f"Triche devrait être détectée"

    print(f"(normal={r1['severity']}, triche={r2['severity']})", end=" ")
    return True

runner.test("Détection d'anomalies", test_anomaly_detection)


def test_zpd_classification():
    from app.models.competence import Competence

    assert Competence.classify_zone(0.90) == "mastered"
    assert Competence.classify_zone(0.60) == "zpd"
    assert Competence.classify_zone(0.20) == "frustration"
    assert Competence.classify_zone(0.85) == "mastered"
    assert Competence.classify_zone(0.40) == "zpd"
    assert Competence.classify_zone(0.39) == "frustration"

    print("(0.90=mastered, 0.60=zpd, 0.20=frustration)", end=" ")
    return True

runner.test("Classification ZPD", test_zpd_classification)


def test_recommend_difficulty():
    from app.services.saint_service import SAINTService

    r1 = SAINTService._recommend_difficulty(0.2, 0.2)
    assert r1["value"] < 0.5, f"Élève faible devrait avoir diff < 0.5, got {r1['value']}"

    r2 = SAINTService._recommend_difficulty(0.9, 0.9)
    assert r2["value"] > 0.7, f"Élève fort devrait avoir diff > 0.7, got {r2['value']}"

    # <= pour gérer les bornes (0.1 et 1.0)
    assert r1["range_min"] <= r1["value"] <= r1["range_max"]
    assert r2["range_min"] <= r2["value"] <= r2["range_max"]

    print(f"(faible→{r1['value']}, fort→{r2['value']})", end=" ")
    return True

runner.test("Difficulté recommandée", test_recommend_difficulty)


def test_confidence():
    from app.services.saint_service import SAINTService

    r1 = SAINTService._compute_confidence(0.5, 2)
    assert r1["level"] == "faible", f"2 interactions devrait donner confiance faible"

    r2 = SAINTService._compute_confidence(0.95, 100)
    assert r2["level"] == "haute", f"100 interactions + P=0.95 devrait donner haute confiance"

    print(f"(n=2→{r1['level']}, n=100→{r2['level']})", end=" ")
    return True

runner.test("Score de confiance", test_confidence)


def test_empty_result():
    from app.services.saint_service import SAINTService

    r = SAINTService._empty_result("test_comp_id")

    required_keys = [
        "p_correct", "mastery", "zone", "zone_label",
        "estimated_attempts", "hint_probability",
        "engagement", "anomaly", "recommended_difficulty",
        "recommended_exercises_count", "confidence"
    ]
    for key in required_keys:
        assert key in r, f"Clé manquante dans empty_result: {key}"

    assert r["p_correct"] == 0.5
    assert r["mastery"] == 0.0
    print(f"({len(required_keys)} clés vérifiées)", end=" ")
    return True

runner.test("Résultat vide (pas de données)", test_empty_result)


# ═══════════════════════════════════════════════
# TEST 4 : Fallback sans modèle
# ═══════════════════════════════════════════════

runner.section("TEST 4 — Mode fallback")


def test_fallback_predict():
    from app.services.saint_service import SAINTService

    saved_model = SAINTService._model
    SAINTService._model = None

    try:
        assert not SAINTService.is_loaded()
        result = SAINTService._empty_result("test")
        assert result["p_correct"] == 0.5
        assert "zone" in result
        print("(fallback retourne résultat valide)", end=" ")
        return True
    finally:
        SAINTService._model = saved_model

runner.test("Fallback sans modèle chargé", test_fallback_predict)


# ═══════════════════════════════════════════════
# TEST 5 : Intégration MongoDB Atlas
# ═══════════════════════════════════════════════

runner.section("TEST 5 — Intégration MongoDB Atlas")


def test_mongodb_connection():
    """Teste la connexion à MongoDB Atlas."""
    from pymongo import MongoClient

    client = MongoClient(MONGO_URI)
    # Ping pour vérifier la connexion
    client.admin.command('ping')
    client.close()
    print("(connexion réussie)", end=" ")
    return True

runner.test("Connexion à MongoDB Atlas", test_mongodb_connection)


def test_saint_service_load():
    from app.services.saint_service import SAINTService

    SAINTService._model = None
    SAINTService._config = None
    SAINTService._data_info = None

    SAINTService.load_model()

    assert SAINTService.is_loaded(), "Le modèle devrait être chargé"
    assert SAINTService._config is not None
    assert SAINTService._data_info is not None

    print(f"(n_exercises={SAINTService._data_info['n_exercises']}, "
          f"n_skills={SAINTService._data_info['n_skills']})", end=" ")
    return True

runner.test("SAINTService.load_model()", test_saint_service_load)


def test_mongodb_integration():
    """Test complet avec MongoDB Atlas."""
    try:
        from pymongo import MongoClient
        from bson import ObjectId
        from app.services.saint_service import SAINTService

        if not SAINTService.is_loaded():
            SAINTService.load_model()

        client = MongoClient(MONGO_URI)
        db = client["adaptive_learning_test_saint"]

        # Nettoyer
        db["user_responses"].drop()
        db["user_progress"].drop()

        # Créer des réponses fictives
        user_id = "test_user_saint"
        comp_id = ObjectId()
        ex_ids = [ObjectId() for _ in range(15)]
        now = datetime.utcnow()

        responses = []
        for i in range(15):
            responses.append({
                "user_id": user_id,
                "exercise_id": ex_ids[i % len(ex_ids)],
                "competence_id": comp_id,
                "lesson_id": ObjectId(),
                "answer": "test",
                "is_correct": i % 3 != 0,
                "time_spent": 20 + i * 5,
                "created_at": now - timedelta(minutes=15 - i),
            })

        db["user_responses"].insert_many(responses)

        count = db["user_responses"].count_documents({"user_id": user_id})
        assert count == 15, f"Devrait avoir 15 réponses, got {count}"

        # Prédiction SAINT+
        result = SAINTService.predict(db, user_id, str(comp_id))

        # Vérifier la structure
        assert "p_correct" in result
        assert "mastery" in result
        assert "zone" in result
        assert "engagement" in result
        assert "anomaly" in result

        p = result["p_correct"]
        assert 0.0 <= p <= 1.0, f"P(correct) hors bornes: {p}"

        print(f"\n    P(correct)  = {result['p_correct']}")
        print(f"    Mastery     = {result['mastery']}")
        print(f"    Zone        = {result['zone']}")
        print(f"    Engagement  = {result['engagement']['score']:.2f} ({result['engagement']['level']})")
        print(f"    Hint        = {result['hint_probability']['probability']:.2f} ({result['hint_probability']['level']})")
        print(f"    Anomalie    = {result['anomaly']['has_anomaly']}")
        print(f"    Tentatives  = {result['estimated_attempts']['value']}")
        print(f"    Confiance   = {result['confidence']['level']}")
        print(f"    Difficulté  = {result['recommended_difficulty']['value']}", end=" ")

        # Nettoyer
        client.drop_database("adaptive_learning_test_saint")
        client.close()
        return True

    except Exception as e:
        try:
            client.drop_database("adaptive_learning_test_saint")
            client.close()
        except:
            pass
        raise e

runner.test("Intégration complète MongoDB Atlas + SAINT+", test_mongodb_integration)


# ═══════════════════════════════════════════════
# TEST 6 : Simulation parcours élève
# ═══════════════════════════════════════════════

runner.section("TEST 6 — Simulation parcours élève complet")


def test_student_journey():
    """Simule un parcours complet sur MongoDB Atlas."""
    try:
        from pymongo import MongoClient
        from bson import ObjectId
        from app.services.saint_service import SAINTService

        if not SAINTService.is_loaded():
            SAINTService.load_model()

        client = MongoClient(MONGO_URI)
        db = client["adaptive_learning_test_journey"]
        db["user_responses"].drop()

        user_id = "journey_student"
        comp_id = ObjectId()
        now = datetime.utcnow()
        predictions = []

        # Phase 0 : Pas de données
        r0 = SAINTService.predict(db, user_id, str(comp_id))
        predictions.append(("Phase 0 (vide)", r0["p_correct"], r0["zone"]))

        # Phase 1 : Exercices faciles (4/5 correct)
        for i in range(5):
            db["user_responses"].insert_one({
                "user_id": user_id,
                "exercise_id": ObjectId(),
                "competence_id": comp_id,
                "lesson_id": ObjectId(),
                "answer": "test",
                "is_correct": i != 2,
                "time_spent": 25,
                "created_at": now - timedelta(minutes=30 - i),
            })

        r1 = SAINTService.predict(db, user_id, str(comp_id))
        predictions.append(("Phase 1 (facile)", r1["p_correct"], r1["zone"]))

        # Phase 2 : Exercices moyens (3/5 correct)
        for i in range(5):
            db["user_responses"].insert_one({
                "user_id": user_id,
                "exercise_id": ObjectId(),
                "competence_id": comp_id,
                "lesson_id": ObjectId(),
                "answer": "test",
                "is_correct": i < 3,
                "time_spent": 45,
                "created_at": now - timedelta(minutes=20 - i),
            })

        r2 = SAINTService.predict(db, user_id, str(comp_id))
        predictions.append(("Phase 2 (moyen)", r2["p_correct"], r2["zone"]))

        # Phase 3 : Exercices difficiles (1/5 correct)
        for i in range(5):
            db["user_responses"].insert_one({
                "user_id": user_id,
                "exercise_id": ObjectId(),
                "competence_id": comp_id,
                "lesson_id": ObjectId(),
                "answer": "test",
                "is_correct": i == 0,
                "time_spent": 90,
                "created_at": now - timedelta(minutes=10 - i),
            })

        r3 = SAINTService.predict(db, user_id, str(comp_id))
        predictions.append(("Phase 3 (difficile)", r3["p_correct"], r3["zone"]))

        # Afficher le parcours
        print()
        print(f"    {'Phase':<25} {'P(correct)':>12} {'Zone':>15}")
        print(f"    {'─'*25} {'─'*12} {'─'*15}")
        for phase, p, zone in predictions:
            print(f"    {phase:<25} {p:>10.4f}   {zone:>15}")

        # Vérification
        assert r1["p_correct"] > r0["p_correct"], \
            "Après exercices faciles, P devrait augmenter"

        print(f"\n    ✅ Évolution cohérente du parcours", end=" ")

        # Nettoyer
        client.drop_database("adaptive_learning_test_journey")
        client.close()
        return True

    except Exception as e:
        try:
            client.drop_database("adaptive_learning_test_journey")
            client.close()
        except:
            pass
        raise e

runner.test("Simulation parcours élève", test_student_journey)


def test_enriched_output_structure():
    """Vérifie la structure complète du JSON de sortie."""
    try:
        from pymongo import MongoClient
        from bson import ObjectId
        from app.services.saint_service import SAINTService

        client = MongoClient(MONGO_URI)
        db = client["adaptive_learning_test_structure"]
        db["user_responses"].drop()

        user_id = "structure_test"
        comp_id = ObjectId()
        now = datetime.utcnow()

        for i in range(10):
            db["user_responses"].insert_one({
                "user_id": user_id,
                "exercise_id": ObjectId(),
                "competence_id": comp_id,
                "lesson_id": ObjectId(),
                "answer": "x",
                "is_correct": i % 2 == 0,
                "time_spent": 30,
                "created_at": now - timedelta(minutes=10 - i),
            })

        result = SAINTService.predict(db, user_id, str(comp_id))

        checks = {
            "p_correct": lambda v: isinstance(v, float) and 0 <= v <= 1,
            "mastery": lambda v: isinstance(v, float) and 0 <= v <= 1,
            "zone": lambda v: v in ("mastered", "zpd", "frustration"),
            "zone_label": lambda v: isinstance(v, str) and len(v) > 0,
            "is_ready_to_learn": lambda v: isinstance(v, bool),
            "estimated_attempts": lambda v: isinstance(v, dict) and "value" in v,
            "hint_probability": lambda v: isinstance(v, dict) and "probability" in v,
            "engagement": lambda v: isinstance(v, dict) and "score" in v,
            "anomaly": lambda v: isinstance(v, dict) and "has_anomaly" in v,
            "recommended_difficulty": lambda v: isinstance(v, dict) and "value" in v,
            "recommended_exercises_count": lambda v: isinstance(v, dict) and "count" in v,
            "confidence": lambda v: isinstance(v, dict) and "score" in v,
        }

        all_ok = True
        for key, validator in checks.items():
            if key not in result:
                print(f"\n    ❌ Clé manquante: {key}", end="")
                all_ok = False
            elif not validator(result[key]):
                print(f"\n    ❌ Valeur invalide pour {key}: {result[key]}", end="")
                all_ok = False

        if all_ok:
            print(f"({len(checks)} champs validés)", end=" ")

        client.drop_database("adaptive_learning_test_structure")
        client.close()
        return all_ok or "Certains champs sont invalides"

    except Exception as e:
        try:
            client.drop_database("adaptive_learning_test_structure")
            client.close()
        except:
            pass
        raise e

runner.test("Structure JSON de sortie complète", test_enriched_output_structure)


# ═══════════════════════════════════════════════
# RÉSUMÉ
# ═══════════════════════════════════════════════

all_passed = runner.summary()
sys.exit(0 if all_passed else 1)
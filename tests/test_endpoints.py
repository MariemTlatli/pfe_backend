"""
Test des endpoints HTTP — SAINT+ intégration.

Prérequis :
  1. Lancer le serveur : python run.py
  2. Avoir seedé les données : python scripts/seed_test_data.py

Usage :
  python tests/test_endpoints.py
"""

import requests
import json
import os
import sys
import time

# ═══════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════

BASE_URL = "http://localhost:5000/api"

# Charger les IDs du seed
IDS_PATH = "data/test_ids.json"
if not os.path.exists(IDS_PATH):
    print(f"❌ Fichier {IDS_PATH} introuvable.")
    print(f"   Lancez d'abord : python scripts/seed_test_data.py")
    sys.exit(1)

with open(IDS_PATH) as f:
    TEST_DATA = json.load(f)

USER_ID = TEST_DATA["user_id"]
COMP_IDS = TEST_DATA["competence_ids"]
EX_IDS = TEST_DATA["exercise_ids"]
CORRECT = TEST_DATA["correct_answer"]
WRONG = TEST_DATA["wrong_answer"]


# ═══════════════════════════════════════════════
# Utilitaires
# ═══════════════════════════════════════════════

passed = 0
failed = 0
total = 0


def test(name, method, url, expected_status, body=None, check_fields=None):
    """Exécute un test HTTP."""
    global passed, failed, total
    total += 1

    print(f"\n{'─'*60}")
    print(f"🧪 Test {total}: {name}")
    print(f"   {method} {url}")

    try:
        if method == "GET":
            r = requests.get(url, timeout=30)
        elif method == "POST":
            r = requests.post(url, json=body, timeout=30)
        elif method == "DELETE":
            r = requests.delete(url, timeout=30)
        else:
            print(f"   ❌ Méthode inconnue: {method}")
            failed += 1
            return None

        # Vérifier le status code
        if r.status_code != expected_status:
            print(f"   ❌ Status: {r.status_code} (attendu {expected_status})")
            print(f"   Response: {r.text[:200]}")
            failed += 1
            return None

        print(f"   ✅ Status: {r.status_code}")

        # Parser le JSON
        try:
            data = r.json()
        except:
            print(f"   ⚠️ Pas de JSON dans la réponse")
            passed += 1
            return None

        # Vérifier les champs attendus
        if check_fields:
            for field in check_fields:
                if field not in data:
                    print(f"   ❌ Champ manquant: {field}")
                    failed += 1
                    return data
                else:
                    val = data[field]
                    # Tronquer si trop long
                    val_str = str(val)
                    if len(val_str) > 80:
                        val_str = val_str[:80] + "..."
                    print(f"   📋 {field}: {val_str}")

        passed += 1
        return data

    except requests.exceptions.ConnectionError:
        print(f"   💥 ERREUR: Impossible de se connecter à {BASE_URL}")
        print(f"      → Le serveur Flask est-il lancé ? (python run.py)")
        failed += 1
        return None
    except Exception as e:
        print(f"   💥 ERREUR: {e}")
        failed += 1
        return None


# ═══════════════════════════════════════════════
# Vérifier que le serveur est lancé
# ═══════════════════════════════════════════════

print("\n" + "=" * 60)
print("🚀 TEST DES ENDPOINTS — SAINT+ INTÉGRATION")
print("=" * 60)

print(f"\n  Serveur    : {BASE_URL}")
print(f"  User       : {USER_ID}")
print(f"  Compétences: {len(COMP_IDS)}")
print(f"  Exercices  : {len(EX_IDS)}")

try:
    r = requests.get(f"{BASE_URL.replace('/api', '')}/docs", timeout=5)
    print(f"  Connexion  : ✅ OK")
except:
    print(f"\n  ❌ Le serveur n'est pas lancé !")
    print(f"     Lancez : python run.py")
    print(f"     Puis relancez ce test.")
    sys.exit(1)


# ═══════════════════════════════════════════════
# TEST A : Historique vide au départ
# ═══════════════════════════════════════════════

print(f"\n\n{'='*60}")
print(f"📦 PHASE A — État initial")
print(f"{'='*60}")

test(
    "Historique vide",
    "GET",
    f"{BASE_URL}/responses/user/{USER_ID}/history",
    200,
    check_fields=["user_id", "count", "responses"]
)


# ═══════════════════════════════════════════════
# TEST B : Soumettre des réponses (avec SAINT+)
# ═══════════════════════════════════════════════

print(f"\n\n{'='*60}")
print(f"📝 PHASE B — Soumission de réponses + SAINT+")
print(f"{'='*60}")

# B1 : Réponse CORRECTE
result_b1 = test(
    "Soumettre réponse CORRECTE",
    "POST",
    f"{BASE_URL}/responses/submit",
    201,
    body={
        "user_id": USER_ID,
        "exercise_id": EX_IDS[0],
        "answer": CORRECT,
        "time_spent": 30
    },
    check_fields=["is_correct", "saint_prediction"]
)

if result_b1 and "saint_prediction" in result_b1:
    sp = result_b1["saint_prediction"]
    print(f"\n   🧠 SAINT+ Prédiction :")
    print(f"      P(correct)  = {sp.get('p_correct')}")
    print(f"      Mastery     = {sp.get('mastery')}")
    print(f"      Zone        = {sp.get('zone')}")
    print(f"      Zone Label  = {sp.get('zone_label')}")
    print(f"      Maîtrisé    = {sp.get('is_mastered')}")
    if sp.get("engagement"):
        print(f"      Engagement  = {sp['engagement'].get('score')} ({sp['engagement'].get('level')})")
    if sp.get("hint"):
        hint = sp["hint"]
        if isinstance(hint, dict):
            print(f"      Hint        = {hint.get('probability')} ({hint.get('level')})")
        else:
            print(f"      Hint        = {hint}")
    if sp.get("confidence"):
        print(f"      Confiance   = {sp['confidence'].get('level')}")

# B2 : Réponse INCORRECTE
result_b2 = test(
    "Soumettre réponse INCORRECTE",
    "POST",
    f"{BASE_URL}/responses/submit",
    201,
    body={
        "user_id": USER_ID,
        "exercise_id": EX_IDS[1],
        "answer": WRONG,
        "time_spent": 45
    },
    check_fields=["is_correct", "saint_prediction"]
)

# B3-B6 : Plusieurs réponses pour enrichir l'historique
print(f"\n   📝 Soumission de 4 réponses supplémentaires...")
for i in range(4):
    ex_idx = (i + 2) % len(EX_IDS)
    is_correct_answer = CORRECT if i % 2 == 0 else WRONG
    time_s = 20 + i * 15

    r = requests.post(f"{BASE_URL}/responses/submit", json={
        "user_id": USER_ID,
        "exercise_id": EX_IDS[ex_idx],
        "answer": is_correct_answer,
        "time_spent": time_s
    })
    status = "✅" if r.status_code == 201 else "❌"
    answer_label = "correct" if is_correct_answer == CORRECT else "faux"
    print(f"      Réponse {i+3}: {status} ({answer_label}, {time_s}s)")


# ═══════════════════════════════════════════════
# TEST C : Vérifier l'historique après soumissions
# ═══════════════════════════════════════════════

print(f"\n\n{'='*60}")
print(f"📊 PHASE C — Vérification de l'historique")
print(f"{'='*60}")

test(
    "Historique après 6 réponses",
    "GET",
    f"{BASE_URL}/responses/user/{USER_ID}/history",
    200,
    check_fields=["user_id", "count"]
)

test(
    "Stats globales",
    "GET",
    f"{BASE_URL}/responses/user/{USER_ID}/stats",
    200,
    check_fields=["total", "correct", "incorrect", "success_rate"]
)

test(
    "Stats par compétence",
    "GET",
    f"{BASE_URL}/responses/user/{USER_ID}/stats/{COMP_IDS[0]}",
    200,
    check_fields=["total", "correct", "success_rate"]
)

test(
    "Résumé par compétences",
    "GET",
    f"{BASE_URL}/responses/user/{USER_ID}/summary",
    200,
    check_fields=["user_id", "competences_worked", "summary"]
)


# ═══════════════════════════════════════════════
# TEST D : Prédiction SAINT+ (sans soumettre)
# ═══════════════════════════════════════════════

print(f"\n\n{'='*60}")
print(f"🧠 PHASE D — Prédiction SAINT+ directe")
print(f"{'='*60}")

result_d1 = test(
    "Prédiction globale",
    "GET",
    f"{BASE_URL}/responses/predict/{USER_ID}",
    200,
    check_fields=["user_id", "prediction"]
)

if result_d1 and "prediction" in result_d1:
    pred = result_d1["prediction"]
    print(f"\n   🧠 Prédiction complète :")
    print(f"      P(correct)           = {pred.get('p_correct')}")
    print(f"      Mastery              = {pred.get('mastery')}")
    print(f"      Zone                 = {pred.get('zone')}")
    print(f"      Tentatives estimées  = {pred.get('estimated_attempts')}")
    print(f"      Besoin indice        = {pred.get('hint_probability')}")
    print(f"      Engagement           = {pred.get('engagement')}")
    print(f"      Anomalie             = {pred.get('anomaly')}")
    print(f"      Difficulté recom.    = {pred.get('recommended_difficulty')}")
    print(f"      Exercices recom.     = {pred.get('recommended_exercises_count')}")
    print(f"      Confiance            = {pred.get('confidence')}")

result_d2 = test(
    "Prédiction par compétence",
    "GET",
    f"{BASE_URL}/responses/predict/{USER_ID}?competence_id={COMP_IDS[0]}",
    200,
    check_fields=["user_id", "competence_id", "prediction"]
)


# ═══════════════════════════════════════════════
# TEST E : Progression
# ═══════════════════════════════════════════════

print(f"\n\n{'='*60}")
print(f"📈 PHASE E — Progression SAINT+")
print(f"{'='*60}")

test(
    "Progression globale",
    "GET",
    f"{BASE_URL}/responses/progress/{USER_ID}",
    200,
    check_fields=["user_id", "competences_count", "progresses"]
)


# ═══════════════════════════════════════════════
# TEST F : Scénario d'apprentissage progressif
# ═══════════════════════════════════════════════

print(f"\n\n{'='*60}")
print(f"🎓 PHASE F — Scénario d'apprentissage progressif")
print(f"{'='*60}")

print(f"\n   Simulation : 10 réponses correctes d'affilée")
print(f"   sur la compétence 1 (Variables Python)")
print(f"   {'─'*50}")

predictions_over_time = []

for i in range(10):
    r = requests.post(f"{BASE_URL}/responses/submit", json={
        "user_id": USER_ID,
        "exercise_id": EX_IDS[0],  # Même exercice, compétence 1
        "answer": CORRECT,
        "time_spent": 25 + i * 2
    })

    if r.status_code == 201:
        data = r.json()
        sp = data.get("saint_prediction", {})
        p = sp.get("p_correct", "?")
        m = sp.get("mastery", "?")
        z = sp.get("zone", "?")

        predictions_over_time.append((i + 1, p, m, z))
        print(f"      Réponse {i+1:>2}: P={p}, mastery={m}, zone={z}")
    else:
        print(f"      Réponse {i+1:>2}: ❌ erreur {r.status_code}")

if predictions_over_time:
    print(f"\n   📊 Évolution :")
    print(f"      {'#':>3} {'P(correct)':>12} {'Mastery':>10} {'Zone':>15}")
    print(f"      {'─'*3} {'─'*12} {'─'*10} {'─'*15}")
    for step, p, m, z in predictions_over_time:
        p_str = f"{p:.4f}" if isinstance(p, float) else str(p)
        m_str = f"{m:.4f}" if isinstance(m, float) else str(m)
        print(f"      {step:>3} {p_str:>12} {m_str:>10} {z:>15}")


# ═══════════════════════════════════════════════
# TEST G : Nettoyage
# ═══════════════════════════════════════════════

print(f"\n\n{'='*60}")
print(f"🧹 PHASE G — Nettoyage")
print(f"{'='*60}")

test(
    "Supprimer historique utilisateur test",
    "DELETE",
    f"{BASE_URL}/responses/user/{USER_ID}",
    200,
    check_fields=["deleted_count"]
)


# ═══════════════════════════════════════════════
# RÉSUMÉ FINAL
# ═══════════════════════════════════════════════

print(f"\n\n{'='*60}")
print(f"📊 RÉSUMÉ FINAL")
print(f"{'='*60}")
print(f"\n  Total  : {total}")
print(f"  ✅ Pass : {passed}")
print(f"  ❌ Fail : {failed}")
print(f"\n  {'✅ TOUS LES TESTS PASSENT !' if failed == 0 else '❌ CERTAINS TESTS ÉCHOUENT'}")
print(f"{'='*60}")
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient
import requests
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = "mongodb+srv://crud:H24ZJZXDzDOoVYKD@cluster0.gjtsy.mongodb.net/"
DB_NAME = "adaptive_learning_db"
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]


# ─────────────────────────────────────────────────────────────
# ⏱️ HELPER : Format timestamp compatible Marshmallow
# ─────────────────────────────────────────────────────────────
def format_iso_timestamp(dt=None):
    """Format ISO 8601 avec 'Z' pour Marshmallow fields.DateTime()"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


# ─────────────────────────────────────────────────────────────
# 📄 EXPORT DES IDs DANS UN FICHIER JSON (enrichi)
# ─────────────────────────────────────────────────────────────
def export_ids(seeded_dict, filepath: str = "generated_ids.json"):
    """Exporte tous les IDs avec mapping par compétence et difficulté"""
    export = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domains": {name: str(_id) for name, _id in seeded_data["domain_ids"].items()},
        "subjects": {name: str(_id) for name, _id in seeded_data["subject_ids"].items()},
        "competences": {name: str(_id) for name, _id in seeded_data["competence_ids"].items()},
        "exercises": {
            "all_ids": seeded_data["exercise_ids"],
            "by_competence": {},      # {competence: [exercise_ids]}
            "by_difficulty": {}       # {difficulty: {competence: exercise_id}}
        },
        "quick_reference": {}         # Rempli dynamiquement ci-dessous
    }
    
    # Parcourir tous les exercices pour les mapper
    for ex_id in seeded_data["exercise_ids"]:
        ex = db.exercises.find_one({"_id": ObjectId(ex_id)})
        if not ex:
            continue
            
        # Trouver le nom de la compétence
        comp_name = next(
            (name for name, cid in seeded_data["competence_ids"].items() 
             if str(cid) == str(ex["competence_id"])),
            None
        )
        if not comp_name:
            continue
        
        difficulty = ex.get("difficulty", 0.0)
        diff_key = f"d{int(difficulty*10)}"  # "d1", "d3", "d5", etc.
        
        # Mapper par compétence
        if comp_name not in export["exercises"]["by_competence"]:
            export["exercises"]["by_competence"][comp_name] = []
        export["exercises"]["by_competence"][comp_name].append(ex_id)
        
        # Mapper par difficulté
        if diff_key not in export["exercises"]["by_difficulty"]:
            export["exercises"]["by_difficulty"][diff_key] = {}
        export["exercises"]["by_difficulty"][diff_key][comp_name] = ex_id
        
        # Quick reference pour tests rapides
        ref_key = f"{comp_name}_d{int(difficulty*10)}"
        export["quick_reference"][ref_key] = {
            "exercise_id": ex_id,
            "competence_id": str(ex["competence_id"]),
            "difficulty": difficulty,
            "correct_answer": ex.get("correct_answer"),
            "question_preview": ex.get("question", "")[:40] + "..."
        }
    
    # Sauvegarder
    Path(filepath).write_text(json.dumps(export, indent=2, ensure_ascii=False))
    print(f"📄 IDs exportés dans {filepath} ({len(export['quick_reference'])} références)")
    return export


# ─────────────────────────────────────────────────────────────
# 🎯 SÉLECTION AUTOMATIQUE D'UN EXERCICE (avec niveau de difficulté)
# ─────────────────────────────────────────────────────────────
def select_exercise(seeded_dict, db, auto_select: str = "addition", 
                   target_difficulty: float = None):
    """
    Sélectionne un exercice par compétence et optionally par difficulté cible.
    
    Args:
        auto_select: Nom de la compétence
        target_difficulty: Difficulté cible (None = premier disponible)
    
    Returns:
        tuple: (exercise_id, competence_id, exercise_doc)
    """
    if not auto_select or auto_select not in seeded_data["competence_ids"]:
        logger.error(f"❌ Compétence '{auto_select}' inconnue")
        return None, None, None
    
    competence_id = seeded_data["competence_ids"][auto_select]
    
    # Construire la requête de filtrage
    query = {"competence_id": competence_id}
    if target_difficulty is not None:
        query["difficulty"] = target_difficulty
    
    # Trouver l'exercice
    exercise = db.exercises.find_one(query, sort=[("difficulty", 1)])
    
    if not exercise:
        # Fallback: prendre le premier exercice de la compétence
        exercise = db.exercises.find_one({"competence_id": competence_id})
        if not exercise:
            logger.error(f"❌ Aucun exercice pour '{auto_select}'")
            return None, None, None
        print(f"⚠️ Difficulté {target_difficulty} non trouvée, fallback sur difficulté {exercise.get('difficulty')}")
    
    exercise_id = str(exercise["_id"])
    
    print(f"⚡ Sélection automatique :")
    print(f"   • Compétence  : {auto_select}")
    print(f"   • Difficulty  : {exercise.get('difficulty')}")
    print(f"   • Exercise ID : {exercise_id}")
    print(f"   • Question    : {exercise.get('question', 'N/A')[:50]}...")
    print(f"   • Réponse     : {exercise.get('correct_answer', 'N/A')}")
    
    return exercise_id, str(competence_id), exercise


# ─────────────────────────────────────────────────────────────
# 🧪 TEST SUBMISSION (avec timestamp corrigé)
# ─────────────────────────────────────────────────────────────
def test_submission(api_base_url: str, exercise_id: str, competence_id: str, 
                   exercise_doc: dict, answer_mode: str = "correct"):
    """Teste l'endpoint POST /submit avec payload valide"""
    
    print("\n" + "🧪" * 40)
    print("🚀 Lancement du test de soumission...")
    print("🧪" * 40 + "\n")
    
    # Vérifications MongoDB
    if not db.exercises.find_one({"_id": ObjectId(exercise_id)}):
        print("❌ Exercise non trouvé dans MongoDB")
        return False
    if not db.competences.find_one({"_id": ObjectId(competence_id)}):
        print("❌ Competence non trouvée dans MongoDB")
        return False
    
    # Déterminer la réponse
    correct_answer = exercise_doc.get("correct_answer")
    if answer_mode == "correct":
        answer = correct_answer
    elif answer_mode == "wrong":
        answer = str(int(correct_answer) + 1) if str(correct_answer).isdigit() else "wrong"
    elif answer_mode.startswith("custom:"):
        answer = answer_mode.split(":", 1)[1]
    else:
        answer = correct_answer
    
    # ✅ Payload avec timestamps au format Marshmallow
    payload = {
        "user_id": "69d78b6e9c8ffb339eb0ced2",
        "exercise_id": exercise_id,
        "competence_id": competence_id,
        "answer": answer,
        "time_spent_seconds": 42,
        "hints_used": 1,
        "attempt_number": 1,
        "current_mastery_level": 0.35,
        "current_zpd_zone": "zpd",
        "emotion_data": {
            "dominant_emotion": "happy",
            "confidence": 0.88,
            "frustration_detected": False,
            "average_confidence": 0.85,
            "emotion_history": [
                {"emotion": "sad", "confidence": 0.75, "timestamp": format_iso_timestamp()},
                {"emotion": "happy", "confidence": 0.92, "timestamp": format_iso_timestamp()}
            ]
        }
    }
    
    print(f"📤 Payload :")
    print(f"   • exercise_id:    {exercise_id}")
    print(f"   • answer:         {answer} {'✅' if answer == correct_answer else '❌'}")
    print(f"   • difficulty:     {exercise_doc.get('difficulty')}\n")
    
    # Appel HTTP
    try:
        response = requests.post(
            f"{api_base_url}/submit",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=8000
        )
        
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print("\n✅ SUCCESS (201):")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"\n❌ ERREUR {response.status_code}:")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────────────────────────────
# 🌱 SEED INITIAL DATA (avec 6 exercices par compétence)
# ─────────────────────────────────────────────────────────────
def seed_initial_data(clean_before: bool = True):
    """Seed avec exercices progressifs par niveau de difficulté"""
    
    if clean_before:
        print("🧹 Nettoyage des collections...")
        for coll in ['exercises', 'competences', 'subjects', 'domains', 'user_responses']:
            db[coll].delete_many({})
        print("✅ Collections vidées\n")
    
    # ── DOMAINS ──
    domains_data = [{"name": "Math", "description": "Mathématiques fondamentales", "created_at": datetime.now(timezone.utc)}]
    result = db.domains.insert_many(domains_data)
    domain_ids = {d['name']: _id for d, _id in zip(domains_data, result.inserted_ids)}
    print(f"✅ {len(domain_ids)} domaine(s)")

    # ── SUBJECTS ──
    subjects_data = [{"domain_id": domain_ids["Math"], "name": "calcul de deux nombres", "description": "Opérations de base", "created_at": datetime.now(timezone.utc)}]
    result = db.subjects.insert_many(subjects_data)
    subject_ids = {s['name']: _id for s, _id in zip(subjects_data, result.inserted_ids)}
    print(f"✅ {len(subject_ids)} matière(s)")

    # ── COMPETENCES ──
    competences_data = [
        {"subject_id": subject_ids["calcul de deux nombres"], "name": "addition", "code": "addition", "description": "Addition", "created_at": datetime.now(timezone.utc)},
        {"subject_id": subject_ids["calcul de deux nombres"], "name": "soustraction", "code": "soustraction", "description": "Soustraction", "created_at": datetime.now(timezone.utc)},
        {"subject_id": subject_ids["calcul de deux nombres"], "name": "multiplication", "code": "multiplication", "description": "Multiplication", "created_at": datetime.now(timezone.utc)},
        {"subject_id": subject_ids["calcul de deux nombres"], "name": "division", "code": "division", "description": "Division", "created_at": datetime.now(timezone.utc)},
    ]
    result = db.competences.insert_many(competences_data)
    competence_ids = {c['name']: _id for c, _id in zip(competences_data, result.inserted_ids)}
    print(f"✅ {len(competence_ids)} compétence(s)")

    # ── EXERCICES PROGRESSIFS ──
    lesson_id = ObjectId("69ca581aa4cc4294998499ba")
    
    # Template de difficultés progressives
    difficulties = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    
    exercises_data = []
    
    # 🔹 ADDITION (6 niveaux)
    for i, diff in enumerate(difficulties, 1):
        exercises_data.append({
            "competence_id": competence_ids["addition"], "lesson_id": lesson_id,
            "type": "qcm", "difficulty": diff,
            "question": f"Niveau {i}: Quel est le résultat de {i*2} + {i*3} ?",
            "options": [str(i*2 + i*3), str(i*2 + i*3 - 1), str(i*2 + i*3 + 1), str(i*5)],
            "correct_answer": str(i*2 + i*3),
            "explanation": f"Addition progressive niveau {i}: {i*2} + {i*3} = {i*2 + i*3}",
            "hints": ["Additionnez les deux nombres", "Utilisez la droite numérique"] if i <= 3 else [],
            "code_template": "", "expected_output": "",
            "estimated_time": 30 + i*10, "status": "generated",
            "attempt_count": 0, "success_count": 0,
            "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)
        })
    
    # 🔹 SOUSTRACTION (6 niveaux)
    for i, diff in enumerate(difficulties, 1):
        a, b = i*10, i*3
        exercises_data.append({
            "competence_id": competence_ids["soustraction"], "lesson_id": lesson_id,
            "type": "qcm", "difficulty": diff,
            "question": f"Niveau {i}: Quel est le résultat de {a} - {b} ?",
            "options": [str(a-b), str(a-b-1), str(a-b+1), str(a+b)],
            "correct_answer": str(a-b),
            "explanation": f"Soustraction niveau {i}: {a} - {b} = {a-b}",
            "hints": ["Retirez la plus petite valeur"] if i <= 3 else [],
            "code_template": "", "expected_output": "",
            "estimated_time": 30 + i*10, "status": "generated",
            "attempt_count": 0, "success_count": 0,
            "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)
        })
    
    # 🔹 MULTIPLICATION (6 niveaux)
    for i, diff in enumerate(difficulties, 1):
        a, b = i+1, i+2
        exercises_data.append({
            "competence_id": competence_ids["multiplication"], "lesson_id": lesson_id,
            "type": "qcm", "difficulty": diff,
            "question": f"Niveau {i}: Quel est le résultat de {a} × {b} ?",
            "options": [str(a*b), str(a*b-a), str(a*b+b), str(a+b)],
            "correct_answer": str(a*b),
            "explanation": f"Multiplication niveau {i}: {a} × {b} = {a*b}",
            "hints": ["Pensez aux tables de multiplication"] if i <= 3 else [],
            "code_template": "", "expected_output": "",
            "estimated_time": 40 + i*10, "status": "generated",
            "attempt_count": 0, "success_count": 0,
            "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)
        })
    
    # 🔹 DIVISION (6 niveaux)
    for i, diff in enumerate(difficulties, 1):
        result = i*5
        exercises_data.append({
            "competence_id": competence_ids["division"], "lesson_id": lesson_id,
            "type": "qcm", "difficulty": diff,
            "question": f"Niveau {i}: Quel est le résultat de {result*i} ÷ {i} ?",
            "options": [str(result), str(result-1), str(result+1), str(result*2)],
            "correct_answer": str(result),
            "explanation": f"Division niveau {i}: {result*i} ÷ {i} = {result}",
            "hints": ["Combien de fois {i} dans {result*i} ?"] if i <= 3 else [],
            "code_template": "", "expected_output": "",
            "estimated_time": 40 + i*10, "status": "generated",
            "attempt_count": 0, "success_count": 0,
            "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)
        })
    
    result = db.exercises.insert_many(exercises_data)
    exercise_ids = [str(_id) for _id in result.inserted_ids]
    print(f"✅ {len(exercise_ids)} exercice(s) créé(s) ({len(exercise_ids)//4} par compétence)")
    
    return {
        "domain_ids": domain_ids, "subject_ids": subject_ids,
        "competence_ids": competence_ids, "exercise_ids": exercise_ids,
    }


# ─────────────────────────────────────────────────────────────
# 🎯 MAIN EXECUTION (avec boucle de progression)
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ⚙️ CONFIGURATION
    API_BASE_URL = "http://192.168.100.132:5000/api/responses"
    COMPETENCE_TO_TEST = "addition"
    TEST_ALL_LEVELS = True  # ✅ Tester tous les niveaux de difficulté
    START_DIFFICULTY = 0.1
    EXPORT_FILE = "generated_ids.json"
    
    try:
        # ── 1. Seed ──
        print("🌱 Seed initial...")
        seeded_data = seed_initial_data(clean_before=True)
        print("✅ Seed terminé\n")
        
        # ── 2. Export ──
        print("📄 Export des IDs...")
        ids_export = export_ids(seeded_data, EXPORT_FILE)
        print()
        
        # ── 3. Test de progression ZPD ──
        if TEST_ALL_LEVELS:
            print(f"🎯 Test de progression pour '{COMPETENCE_TO_TEST}'")
            print("─" * 60)
            
            difficulties = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
            results = []
            
            for diff in difficulties:
                print(f"\n📊 Niveau difficulty={diff}")
                
                ex_id, comp_id, ex_doc = select_exercise(
                    seeded_data, db, 
                    auto_select=COMPETENCE_TO_TEST, 
                    target_difficulty=diff
                )
                
                if not ex_id:
                    print(f"⚠️ Exercice non trouvé pour difficulty={diff}")
                    continue
                
                # Simuler une réponse correcte pour faire progresser le mastery
                success = test_submission(
                    api_base_url=API_BASE_URL,
                    exercise_id=ex_id,
                    competence_id=comp_id,
                    exercise_doc=ex_doc,
                    answer_mode="correct"  # ✅ Réponse correcte pour progression
                )
                results.append({"difficulty": diff, "success": success})
                
                # Petite pause entre les tests
                import time
                time.sleep(0.5)
            
            # 📈 Résumé de la progression
            print("\n" + "═" * 60)
            print("📊 RÉSUMÉ DE LA PROGRESSION ZPD")
            print("═" * 60)
            for r in results:
                status = "✅" if r["success"] else "❌"
                print(f"   Difficulty {r['difficulty']:.1f} : {status}")
            
            success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
            print(f"\n🎯 Taux de succès : {success_rate:.0f}%")
            
        else:
            # Test unique (comportement original)
            ex_id, comp_id, ex_doc = select_exercise(seeded_data, db, COMPETENCE_TO_TEST)
            if ex_id:
                test_submission(API_BASE_URL, ex_id, comp_id, ex_doc, answer_mode="correct")
        
        # ── 4. IDs pour tests manuels ──
        print(f"\n📋 IDs exportés dans : {EXPORT_FILE}")
        print(f"💡 Exemple cURL pour niveau facile :")
        ref = ids_export["quick_reference"].get(f"{COMPETENCE_TO_TEST}_d1")
        if ref:
            print(f"curl -X POST {API_BASE_URL}/submit \\")
            print(f"  -H 'Content-Type: application/json' \\")
            print(f"  -d '{{\"user_id\":\"69d78b6e9c8ffb339eb0ced2\",\"exercise_id\":\"{ref['exercise_id']}\",\"competence_id\":\"{ref['competence_id']}\",\"answer\":\"{ref['correct_answer']}\"}}'")
        
    except Exception as e:
        logger.error(f"❌ Erreur critique : {e}", exc_info=True)
        exit(1)
    finally:
        mongo.close()
        print("\n🔌 Connexion MongoDB fermée.")
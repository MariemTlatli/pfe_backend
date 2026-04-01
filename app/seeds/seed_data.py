from datetime import datetime

from pymongo import MongoClient

MONGO_URI = "mongodb+srv://crud:H24ZJZXDzDOoVYKD@cluster0.gjtsy.mongodb.net/"
DB_NAME = "adaptive_learning_db"
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]   # ✅ IMPORTANT

def seed_initial_data():

    domains_data = [
        {
            "name": "Programmation",
            "description": "Sciences informatiques et développement logiciel",
            "created_at": datetime.utcnow()
        },
        {
            "name": "Mathématiques",
            "description": "Mathématiques fondamentales et appliquées",
            "created_at": datetime.utcnow()
        },
        {
            "name": "Sciences",
            "description": "Physique, chimie, biologie",
            "created_at": datetime.utcnow()
        },
        {
            "name": "Langues",
            "description": "Apprentissage des langues étrangères",
            "created_at": datetime.utcnow()
        }
    ]


    result = db.domains.insert_many(domains_data)  # ✅
    print(result.inserted_ids)

    domain_ids = {d['name']: _id for d, _id in zip(domains_data, result.inserted_ids)}

    print(f"✅ {len(domain_ids)} domaines créés")

    subjects_data = [
        # Programmation
        {
            "domain_id": domain_ids["Programmation"],
            "name": "Python pour débutants",
            "description": "Apprendre les bases de la programmation Python",
            "created_at": datetime.utcnow()
        },
        {
            "domain_id": domain_ids["Programmation"],
            "name": "JavaScript moderne",
            "description": "ES6+, async/await, frameworks modernes",
            "created_at": datetime.utcnow()
        },
        {
            "domain_id": domain_ids["Programmation"],
            "name": "Structures de données",
            "description": "Listes, arbres, graphes, algorithmes",
            "created_at": datetime.utcnow()
        },
        
        # Mathématiques
        {
            "domain_id": domain_ids["Mathématiques"],
            "name": "Algèbre linéaire",
            "description": "Vecteurs, matrices, espaces vectoriels",
            "created_at": datetime.utcnow()
        },
        {
            "domain_id": domain_ids["Mathématiques"],
            "name": "Calcul différentiel",
            "description": "Dérivées, intégrales, séries",
            "created_at": datetime.utcnow()
        },
        
        # Sciences
        {
            "domain_id": domain_ids["Sciences"],
            "name": "Physique quantique",
            "description": "Introduction à la mécanique quantique",
            "created_at": datetime.utcnow()
        },
        
        # Langues
        {
            "domain_id": domain_ids["Langues"],
            "name": "Anglais niveau B1",
            "description": "Grammaire, vocabulaire, conversation",
            "created_at": datetime.utcnow()
        }
    ]

    db.subjects.insert_many(subjects_data)  # ✅
    print(f"✅ {len(subjects_data)} matières créées")


# """
# Initialisation des données de base (domaines + matières).
# """

# from datetime import datetime
# import os
# import json
# from pymongo import MongoClient
# from bson import ObjectId
# from datetime import datetime

# MONGO_URI = "mongodb+srv://crud:H24ZJZXDzDOoVYKD@cluster0.gjtsy.mongodb.net/"
# DB_NAME = "adaptive_learning_db"
# mongo = MongoClient(MONGO_URI)

# def seed_initial_data():
#     """Crée les domaines et matières de base si la DB est vide."""
    
#     # # Vérifier si déjà seedé
#     # if mongo.db.domains.count_documents({}) > 0:
#     #     print("ℹ️  Données déjà présentes, seed ignoré")
#     #     return
    
#     # ── DOMAINES ──
#     domains_data = [
#         {
#             "name": "Programmation",
#             "description": "Sciences informatiques et développement logiciel",
#             "created_at": datetime.utcnow()
#         },
#         {
#             "name": "Mathématiques",
#             "description": "Mathématiques fondamentales et appliquées",
#             "created_at": datetime.utcnow()
#         },
#         {
#             "name": "Sciences",
#             "description": "Physique, chimie, biologie",
#             "created_at": datetime.utcnow()
#         },
#         {
#             "name": "Langues",
#             "description": "Apprentissage des langues étrangères",
#             "created_at": datetime.utcnow()
#         }
#     ]
    
#     # Insérer domaines
#     result = mongo.db.domains.insert_many(domains_data)
#     print(result.inserted_ids)
#     domain_ids = {d['name']: _id for d, _id in zip(domains_data, result.inserted_ids)}
    
#     print(f"✅ {len(domain_ids)} domaines créés")
    
#     # ── MATIÈRES ──
#     subjects_data = [
#         # Programmation
#         {
#             "domain_id": domain_ids["Programmation"],
#             "name": "Python pour débutants",
#             "description": "Apprendre les bases de la programmation Python",
#             "created_at": datetime.utcnow()
#         },
#         {
#             "domain_id": domain_ids["Programmation"],
#             "name": "JavaScript moderne",
#             "description": "ES6+, async/await, frameworks modernes",
#             "created_at": datetime.utcnow()
#         },
#         {
#             "domain_id": domain_ids["Programmation"],
#             "name": "Structures de données",
#             "description": "Listes, arbres, graphes, algorithmes",
#             "created_at": datetime.utcnow()
#         },
        
#         # Mathématiques
#         {
#             "domain_id": domain_ids["Mathématiques"],
#             "name": "Algèbre linéaire",
#             "description": "Vecteurs, matrices, espaces vectoriels",
#             "created_at": datetime.utcnow()
#         },
#         {
#             "domain_id": domain_ids["Mathématiques"],
#             "name": "Calcul différentiel",
#             "description": "Dérivées, intégrales, séries",
#             "created_at": datetime.utcnow()
#         },
        
#         # Sciences
#         {
#             "domain_id": domain_ids["Sciences"],
#             "name": "Physique quantique",
#             "description": "Introduction à la mécanique quantique",
#             "created_at": datetime.utcnow()
#         },
        
#         # Langues
#         {
#             "domain_id": domain_ids["Langues"],
#             "name": "Anglais niveau B1",
#             "description": "Grammaire, vocabulaire, conversation",
#             "created_at": datetime.utcnow()
#         }
#     ]
    
#     mongo.db.subjects.insert_many(subjects_data)
#     print(f"✅ {len(subjects_data)} matières créées")


# """
# Seed de données de test pour tester les endpoints SAINT+.

# Usage :
#   python scripts/seed_test_data.py
# """

# import os
# import json
# from pymongo import MongoClient
# from bson import ObjectId
# from datetime import datetime

# MONGO_URI = "mongodb+srv://crud:H24ZJZXDzDOoVYKD@cluster0.gjtsy.mongodb.net/"
# DB_NAME = "adaptive_learning_db"
#     client = MongoClient(MONGO_URI)
#     db = client[DB_NAME]

# def seed():
#     print("\n🌱 Seeding des données de test...")
#     print("=" * 50)

#     client = MongoClient(MONGO_URI)
#     db = client[DB_NAME]

#     # ══════════════════════════════════════
#     # 1. Créer un utilisateur test (ObjectId valide)
#     # ══════════════════════════════════════

#     test_user_oid = ObjectId()  # Génère un vrai ObjectId
#     test_user_id_str = str(test_user_oid)

#     # Vérifier si un user existe déjà dans la collection users
#     existing_user = db["users"].find_one()
#     if existing_user:
#         test_user_oid = existing_user["_id"]
#         test_user_id_str = str(test_user_oid)
#         print(f"\n  ✅ Utilisateur existant trouvé : {test_user_id_str}")
#     else:
#         db["users"].insert_one({
#             "_id": test_user_oid,
#             "username": "test_student",
#             "email": "test@test.com",
#             "created_at": datetime.utcnow()
#         })
#         print(f"\n  ✅ Utilisateur test créé : {test_user_id_str}")

#     # ══════════════════════════════════════
#     # 2. Récupérer ou créer un subject
#     # ══════════════════════════════════════

#     subject = db["subjects"].find_one()
#     if subject:
#         subject_id = subject["_id"]
#         print(f"  ✅ Subject existant : {subject_id}")
#     else:
#         subject_id = db["subjects"].insert_one({
#             "name": "Python Test",
#             "description": "Matière de test",
#             "domain_id": ObjectId(),
#             "created_at": datetime.utcnow()
#         }).inserted_id
#         print(f"  ✅ Subject créé : {subject_id}")

#     # ══════════════════════════════════════
#     # 3. Créer les compétences
#     # ══════════════════════════════════════

#     # Supprimer les anciennes compétences de test
#     db["competences"].delete_many({"code": {"$regex": "^TEST_"}})

#     comps_data = [
#         {
#             "subject_id": subject_id,
#             "code": "TEST_VAR",
#             "name": "Variables Python",
#             "description": "Déclarer et utiliser des variables",
#             "level": 0,
#             "prerequisites": [],
#             "zpd_thresholds": {"mastered": 0.85, "learning": 0.40},
#             "difficulty_params": {"base_difficulty": 0.3, "weight": 1.0,
#                                   "min_exercises": 3, "mastery_exercises": 5},
#             "graph_data": {"x": 0, "y": 0},
#             "created_at": datetime.utcnow(),
#             "updated_at": datetime.utcnow(),
#         },
#         {
#             "subject_id": subject_id,
#             "code": "TEST_COND",
#             "name": "Conditions if/else",
#             "description": "Structures conditionnelles",
#             "level": 1,
#             "prerequisites": [],
#             "zpd_thresholds": {"mastered": 0.85, "learning": 0.40},
#             "difficulty_params": {"base_difficulty": 0.5, "weight": 1.0,
#                                   "min_exercises": 3, "mastery_exercises": 5},
#             "graph_data": {"x": 100, "y": 100},
#             "created_at": datetime.utcnow(),
#             "updated_at": datetime.utcnow(),
#         },
#         {
#             "subject_id": subject_id,
#             "code": "TEST_LOOP",
#             "name": "Boucles for/while",
#             "description": "Structures itératives",
#             "level": 2,
#             "prerequisites": [],
#             "zpd_thresholds": {"mastered": 0.85, "learning": 0.40},
#             "difficulty_params": {"base_difficulty": 0.7, "weight": 1.0,
#                                   "min_exercises": 3, "mastery_exercises": 5},
#             "graph_data": {"x": 200, "y": 200},
#             "created_at": datetime.utcnow(),
#             "updated_at": datetime.utcnow(),
#         },
#     ]

#     result = db["competences"].insert_many(comps_data)
#     comp_ids = result.inserted_ids

#     # Ajouter les prérequis
#     db["competences"].update_one(
#         {"_id": comp_ids[1]},
#         {"$set": {"prerequisites": [{"competence_id": comp_ids[0], "strength": 1.0}]}}
#     )
#     db["competences"].update_one(
#         {"_id": comp_ids[2]},
#         {"$set": {"prerequisites": [{"competence_id": comp_ids[1], "strength": 1.0}]}}
#     )

#     print(f"  ✅ Compétences créées : {len(comp_ids)}")
#     for i, cid in enumerate(comp_ids):
#         print(f"     {comps_data[i]['code']}: {cid}")

#     # ══════════════════════════════════════
#     # 4. Créer une leçon
#     # ══════════════════════════════════════

#     lesson = db["lessons"].find_one()
#     if lesson:
#         lesson_id = lesson["_id"]
#     else:
#         lesson_id = db["lessons"].insert_one({
#             "competence_id": comp_ids[0],
#             "title": "Leçon de test",
#             "content": "Contenu de test",
#             "created_at": datetime.utcnow()
#         }).inserted_id

#     # ══════════════════════════════════════
#     # 5. Créer les exercices
#     # ══════════════════════════════════════

#     # Supprimer les anciens exercices de test
#     db["exercises"].delete_many({"question": {"$regex": "^Question test"}})

#     exercises = []
#     for i, comp_id in enumerate(comp_ids):
#         for j in range(2):
#             difficulty = 0.3 + i * 0.2 + j * 0.1
#             exercises.append({
#                 "competence_id": comp_id,
#                 "lesson_id": lesson_id,
#                 "type": "qcm",
#                 "difficulty": round(difficulty, 2),
#                 "question": f"Question test {i+1}.{j+1} ?",
#                 "options": ["Réponse A", "Réponse B", "Réponse C", "Réponse D"],
#                 "correct_answer": "Réponse A",
#                 "explanation": f"Explication de la question {i+1}.{j+1}",
#                 "hints": [f"Indice {i+1}.{j+1}"],
#                 "code_template": "",
#                 "expected_output": "",
#                 "estimated_time": 60,
#                 "status": "generated",
#                 "attempt_count": 0,
#                 "success_count": 0,
#                 "created_at": datetime.utcnow(),
#                 "updated_at": datetime.utcnow(),
#             })

#     result = db["exercises"].insert_many(exercises)
#     exercise_ids = result.inserted_ids

#     print(f"  ✅ Exercices créés : {len(exercise_ids)}")
#     for i, eid in enumerate(exercise_ids):
#         print(f"     Ex {i+1} (diff={exercises[i]['difficulty']}): {eid}")

#     # ══════════════════════════════════════
#     # 6. Nettoyer les anciennes réponses du test user
#     # ══════════════════════════════════════

#     db["user_responses"].delete_many({"user_id": test_user_oid})
#     db["user_progress"].delete_many({"user_id": test_user_id_str})
#     print(f"  ✅ Ancien historique nettoyé")

#     # ══════════════════════════════════════
#     # 7. Sauvegarder les IDs
#     # ══════════════════════════════════════

#     test_data = {
#         "user_id": test_user_id_str,
#         "competence_ids": [str(c) for c in comp_ids],
#         "exercise_ids": [str(e) for e in exercise_ids],
#         "correct_answer": "Réponse A",
#         "wrong_answer": "Réponse B",
#     }

#     os.makedirs("data", exist_ok=True)
#     with open("data/test_ids.json", "w") as f:
#         json.dump(test_data, f, indent=2)

#     # ══════════════════════════════════════
#     # 8. Vérification
#     # ══════════════════════════════════════

#     print(f"\n{'='*50}")
#     print(f"✅ SEED TERMINÉ — Vérification")
#     print(f"{'='*50}")

#     # Vérifier que les exercices sont bien en base
#     for eid in exercise_ids:
#         ex = db["exercises"].find_one({"_id": eid})
#         status = "✅" if ex else "❌"
#         print(f"  {status} Exercice {eid} trouvable en base")

#     # Vérifier le user
#     user = db["users"].find_one({"_id": test_user_oid})
#     status = "✅" if user else "❌"
#     print(f"  {status} Utilisateur {test_user_id_str} trouvable en base")

#     print(f"\n  📋 IDs pour les tests :")
#     print(f"     USER_ID : {test_user_id_str}")
#     print(f"     COMP 1  : {comp_ids[0]}")
#     print(f"     COMP 2  : {comp_ids[1]}")
#     print(f"     COMP 3  : {comp_ids[2]}")
#     print(f"     EX 1    : {exercise_ids[0]}")
#     print(f"     EX 2    : {exercise_ids[1]}")
#     print(f"     Correct : 'Réponse A'")

#     print(f"\n  📁 IDs sauvegardés dans data/test_ids.json")
#     print(f"\n  ⚠️  Vérifiez que votre .env contient :")
#     print(f"     MONGO_URI=mongodb+srv://crud:H24ZJZXDzDOoVYKD@cluster0.gjtsy.mongodb.net/adaptive_learning_db")
#     print(f"{'='*50}")

#     client.close()


# if __name__ == "__main__":
#     seed()
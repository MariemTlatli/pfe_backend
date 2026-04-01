"""
Modèle Exercise — Exercice généré pour une compétence/leçon.

Types d'exercices :
  - qcm              : Question à choix multiple (1 bonne réponse)
  - qcm_multiple     : QCM à réponses multiples
  - vrai_faux         : Vrai ou Faux
  - texte_a_trous     : Compléter le texte
  - code_completion   : Compléter du code
  - code_libre        : Écrire du code from scratch
  - debugging         : Trouver et corriger l'erreur
  - projet_mini       : Mini-projet guidé
"""

from bson import ObjectId
from datetime import datetime


class Exercise:

    collection_name = "exercises"

    # Types d'exercices valides
    VALID_TYPES = [
        "qcm",
        "qcm_multiple",
        "vrai_faux",
        "texte_a_trous",
        "code_completion",
        "code_libre",
        "debugging",
        "projet_mini",
    ]

    # Statuts possibles
    STATUS_PLANNED = "planned"
    STATUS_GENERATING = "generating"
    STATUS_GENERATED = "generated"
    STATUS_ERROR = "error"

    # ──────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────

    @staticmethod
    def create(competence_id, lesson_id, exercise_type, difficulty,
               question=None, options=None, correct_answer=None,
               explanation=None, hints=None, code_template=None,
               expected_output=None, estimated_time=60, status="planned"):
        """
        Crée un document exercice.

        Args:
            competence_id: ID de la compétence
            lesson_id: ID de la leçon source
            exercise_type: str — type d'exercice (qcm, code_completion, etc.)
            difficulty: float [0.0, 1.0]
            question: str — énoncé de l'exercice
            options: list[str] — choix possibles (QCM)
            correct_answer: str ou list — réponse(s) correcte(s)
            explanation: str — explication de la réponse
            hints: list[str] — indices progressifs
            code_template: str — code de départ (code_completion, debugging)
            expected_output: str — sortie attendue (code_libre)
            estimated_time: int — temps estimé en secondes
            status: str — planned | generating | generated | error

        Returns:
            dict: document prêt pour insertion MongoDB
        """
        if exercise_type not in Exercise.VALID_TYPES:
            raise ValueError(f"Type invalide: {exercise_type}. Valides: {Exercise.VALID_TYPES}")

        return {
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id,
            "lesson_id": ObjectId(lesson_id) if isinstance(lesson_id, str) else lesson_id,
            "type": exercise_type,
            "difficulty": min(max(float(difficulty), 0.0), 1.0),
            "question": question or "",
            "options": options or [],
            "correct_answer": correct_answer or "",
            "explanation": explanation or "",
            "hints": hints or [],
            "code_template": code_template or "",
            "expected_output": expected_output or "",
            "estimated_time": max(int(estimated_time), 10),
            "status": status,
            "attempt_count": 0,
            "success_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    @staticmethod
    def insert(db, exercise_doc):
        """Insère un exercice en base."""
        collection = db[Exercise.collection_name]
        result = collection.insert_one(exercise_doc)
        return result.inserted_id

    @staticmethod
    def insert_many(db, exercise_docs):
        """Insère plusieurs exercices en base."""
        if not exercise_docs:
            return []
        collection = db[Exercise.collection_name]
        result = collection.insert_many(exercise_docs)
        return result.inserted_ids

    @staticmethod
    def get_by_id(db, exercise_id):
        """Récupère un exercice par ID."""
        collection = db[Exercise.collection_name]
        return collection.find_one({
            "_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id
        })

    @staticmethod
    def get_by_competence(db, competence_id, exercise_type=None, status=None):
        """
        Récupère les exercices d'une compétence.

        Args:
            db: connexion MongoDB
            competence_id: ID de la compétence
            exercise_type: filtrer par type (optionnel)
            status: filtrer par statut (optionnel)

        Returns:
            list[dict]
        """
        collection = db[Exercise.collection_name]
        query = {
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        }
        if exercise_type:
            query["type"] = exercise_type
        if status:
            query["status"] = status

        return list(collection.find(query).sort("difficulty", 1))

    @staticmethod
    def get_by_lesson(db, lesson_id, exercise_type=None):
        """Récupère les exercices d'une leçon."""
        collection = db[Exercise.collection_name]
        query = {
            "lesson_id": ObjectId(lesson_id) if isinstance(lesson_id, str) else lesson_id
        }
        if exercise_type:
            query["type"] = exercise_type

        return list(collection.find(query).sort("difficulty", 1))

    @staticmethod
    def get_by_difficulty_range(db, competence_id, min_diff, max_diff, exercise_type=None):
        """
        Récupère les exercices dans une plage de difficulté.

        Args:
            db: connexion MongoDB
            competence_id: ID de la compétence
            min_diff: float — difficulté minimum
            max_diff: float — difficulté maximum
            exercise_type: filtrer par type (optionnel)

        Returns:
            list[dict]
        """
        collection = db[Exercise.collection_name]
        query = {
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id,
            "difficulty": {"$gte": min_diff, "$lte": max_diff},
            "status": Exercise.STATUS_GENERATED,
        }
        if exercise_type:
            query["type"] = exercise_type

        return list(collection.find(query).sort("difficulty", 1))

    @staticmethod
    def update(db, exercise_id, update_fields):
        """Met à jour un exercice."""
        collection = db[Exercise.collection_name]
        update_fields["updated_at"] = datetime.utcnow()
        result = collection.update_one(
            {"_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id},
            {"$set": update_fields}
        )
        return result.modified_count > 0

    @staticmethod
    def update_status(db, exercise_id, status):
        """Met à jour le statut d'un exercice."""
        return Exercise.update(db, exercise_id, {"status": status})

    @staticmethod
    def update_content(db, exercise_id, question, options, correct_answer,
                       explanation, hints=None, code_template=None, expected_output=None):
        """Met à jour le contenu d'un exercice après génération."""
        fields = {
            "question": question,
            "options": options or [],
            "correct_answer": correct_answer,
            "explanation": explanation or "",
            "hints": hints or [],
            "status": Exercise.STATUS_GENERATED,
        }
        if code_template is not None:
            fields["code_template"] = code_template
        if expected_output is not None:
            fields["expected_output"] = expected_output

        return Exercise.update(db, exercise_id, fields)

    @staticmethod
    def increment_attempts(db, exercise_id, correct):
        """Incrémente les compteurs d'un exercice après une tentative."""
        collection = db[Exercise.collection_name]
        update = {
            "$inc": {"attempt_count": 1},
            "$set": {"updated_at": datetime.utcnow()}
        }
        if correct:
            update["$inc"]["success_count"] = 1

        result = collection.update_one(
            {"_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id},
            update
        )
        return result.modified_count > 0

    @staticmethod
    def delete(db, exercise_id):
        """Supprime un exercice."""
        collection = db[Exercise.collection_name]
        result = collection.delete_one({
            "_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id
        })
        return result.deleted_count > 0

    @staticmethod
    def delete_by_competence(db, competence_id):
        """Supprime tous les exercices d'une compétence."""
        collection = db[Exercise.collection_name]
        result = collection.delete_many({
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        })
        return result.deleted_count

    @staticmethod
    def delete_by_lesson(db, lesson_id):
        """Supprime tous les exercices d'une leçon."""
        collection = db[Exercise.collection_name]
        result = collection.delete_many({
            "lesson_id": ObjectId(lesson_id) if isinstance(lesson_id, str) else lesson_id
        })
        return result.deleted_count

    @staticmethod
    def count_by_competence(db, competence_id, status=None):
        """Compte les exercices d'une compétence."""
        collection = db[Exercise.collection_name]
        query = {
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        }
        if status:
            query["status"] = status
        return collection.count_documents(query)

    # ──────────────────────────────────────────────
    # Vérification de réponse
    # ──────────────────────────────────────────────

    @staticmethod
    def check_answer(exercise_doc, user_answer):
        """
        Vérifie si la réponse de l'utilisateur est correcte.

        Args:
            exercise_doc: document exercice depuis MongoDB
            user_answer: str ou list — réponse de l'utilisateur

        Returns:
            dict: {"is_correct": bool, "correct_answer": str, "explanation": str}
        """
        exercise_type = exercise_doc.get("type", "")
        correct = exercise_doc.get("correct_answer", "")

        if exercise_type == "qcm_multiple":
            # Réponses multiples : comparer comme sets
            if isinstance(user_answer, list) and isinstance(correct, list):
                is_correct = set(user_answer) == set(correct)
            else:
                is_correct = False

        elif exercise_type == "vrai_faux":
            # Normaliser : "vrai"/"true"/True → True
            def normalize_bool(val):
                if isinstance(val, bool):
                    return val
                return str(val).lower().strip() in ("vrai", "true", "1", "oui", "yes")
            is_correct = normalize_bool(user_answer) == normalize_bool(correct)

        elif exercise_type in ("code_libre", "code_completion"):
            # Comparaison souple : strip + lower
            user_clean = str(user_answer).strip()
            correct_clean = str(correct).strip()
            is_correct = user_clean == correct_clean

        else:
            # QCM simple, texte à trous : comparaison directe
            is_correct = str(user_answer).strip().lower() == str(correct).strip().lower()

        return {
            "is_correct": is_correct,
            "correct_answer": correct,
            "explanation": exercise_doc.get("explanation", ""),
        }

    # ──────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────

    @staticmethod
    def get_stats(db, competence_id):
        """Stats des exercices d'une compétence."""
        collection = db[Exercise.collection_name]
        comp_id = ObjectId(competence_id) if isinstance(competence_id, str) else competence_id

        pipeline = [
            {"$match": {"competence_id": comp_id}},
            {"$group": {
                "_id": "$type",
                "count": {"$sum": 1},
                "avg_difficulty": {"$avg": "$difficulty"},
                "total_attempts": {"$sum": "$attempt_count"},
                "total_successes": {"$sum": "$success_count"},
            }}
        ]

        results = list(collection.aggregate(pipeline))

        total = sum(r["count"] for r in results)
        by_type = {}
        for r in results:
            success_rate = 0
            if r["total_attempts"] > 0:
                success_rate = round(r["total_successes"] / r["total_attempts"], 3)
            by_type[r["_id"]] = {
                "count": r["count"],
                "avg_difficulty": round(r["avg_difficulty"], 3),
                "total_attempts": r["total_attempts"],
                "success_rate": success_rate,
            }

        return {
            "competence_id": str(comp_id),
            "total_exercises": total,
            "by_type": by_type,
        }

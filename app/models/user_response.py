"""
Modèle UserResponse — Réponse d'un utilisateur à un exercice.

Chaque fois qu'un utilisateur soumet une réponse, on stocke :
- Ce qu'il a répondu
- Si c'était correct
- Le temps passé
- Les métadonnées (exercice, compétence, leçon)

Ces données alimentent ensuite le BKT (étape 7).
"""

from app.models import UserProgress
from bson import ObjectId
from datetime import datetime


class UserResponse:

    collection_name = "user_responses"

    # ──────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────

    @staticmethod
    def create(user_id, exercise_id, competence_id, lesson_id,
               answer, is_correct, time_spent=0):
        """
        Crée un document réponse utilisateur.

        Args:
            user_id: ID de l'utilisateur
            exercise_id: ID de l'exercice
            competence_id: ID de la compétence
            lesson_id: ID de la leçon
            answer: réponse de l'utilisateur (str, list, bool)
            is_correct: bool — réponse correcte ou non
            time_spent: int — temps en secondes

        Returns:
            dict: document prêt pour insertion MongoDB
        """
        return {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "exercise_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id,
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id,
            "lesson_id": ObjectId(lesson_id) if isinstance(lesson_id, str) else lesson_id,
            "answer": answer,
            "is_correct": bool(is_correct),
            "time_spent": max(int(time_spent), 0),
            "created_at": datetime.utcnow(),
        }

    @staticmethod
    def insert(db, response_doc):
        """Insère une réponse en base."""
        collection = db[UserResponse.collection_name]
        result = collection.insert_one(response_doc)
        return result.inserted_id

    @staticmethod
    def get_by_id(db, response_id):
        """Récupère une réponse par ID."""
        collection = db[UserResponse.collection_name]
        return collection.find_one({
            "_id": ObjectId(response_id) if isinstance(response_id, str) else response_id
        })

    # ──────────────────────────────────────────────
    # Requêtes par utilisateur
    # ──────────────────────────────────────────────

    @staticmethod
    def get_by_user(db, user_id, limit=50):
        """Récupère les dernières réponses d'un utilisateur."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id
            })
            .sort("created_at", -1)
            .limit(limit)
        )

    @staticmethod
    def get_by_user_and_competence(db, user_id, competence_id):
        """Récupère toutes les réponses d'un utilisateur pour une compétence."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
                "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id,
            })
            .sort("created_at", 1)
        )

    @staticmethod
    def get_by_user_and_exercise(db, user_id, exercise_id):
        """Récupère toutes les tentatives d'un utilisateur sur un exercice."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
                "exercise_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id,
            })
            .sort("created_at", 1)
        )

    @staticmethod
    def get_by_user_and_lesson(db, user_id, lesson_id):
        """Récupère les réponses d'un utilisateur pour une leçon."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
                "lesson_id": ObjectId(lesson_id) if isinstance(lesson_id, str) else lesson_id,
            })
            .sort("created_at", 1)
        )

    # ──────────────────────────────────────────────
    # Historique pour BKT
    # ──────────────────────────────────────────────

    @staticmethod
    def get_correctness_history(db, user_id, competence_id):
        """
        Retourne l'historique de correct/faux pour BKT.

        Returns:
            list[bool]: [True, False, True, True, ...]
            Ordonné du plus ancien au plus récent.
        """
        responses = UserResponse.get_by_user_and_competence(db, user_id, competence_id)
        return [r["is_correct"] for r in responses]

    @staticmethod
    def get_last_n_responses(db, user_id, competence_id, n=10):
        """Récupère les N dernières réponses pour une compétence."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
                "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id,
            })
            .sort("created_at", -1)
            .limit(n)
        )

    # ──────────────────────────────────────────────
    # Stats par utilisateur
    # ──────────────────────────────────────────────

    @staticmethod
    def get_user_stats(db, user_id, competence_id=None):
        """
        Statistiques d'un utilisateur.

        Args:
            db: connexion MongoDB
            user_id: ID utilisateur
            competence_id: filtrer par compétence (optionnel)

        Returns:
            dict: {total, correct, incorrect, success_rate, avg_time, streak}
        """
         # ✅ Utiliser la BONNE collection
        collection = db["user_responses"]  
        
        # Ne PAS convertir en ObjectId si stockés en string
        query = {
            "user_id": user_id  # garde en string
        }
        if competence_id:
            query["competence_id"] = competence_id
        responses1 = list(collection.find(query))
        print(responses1)    

        collection = db["user_progress"]
        
        query2 = {
            "user_id": user_id  # garde en string
        }
        if competence_id:
            query2["competence_id"] = ObjectId(competence_id) if isinstance(competence_id, str) else competence_id

        responses2 = list(collection.find(query2))
        print(responses2)   
        print(responses2)
        if not responses2:
            return {
                "total": 0,
                "correct": 0,
                "incorrect": 0,
                "success_rate": 0.0,
                "avg_time": 0,
                "streak": 0,
                "best_streak": 0,
            }

        totalProgress = len(responses1)
        totalReponses = len(responses2)
        correct = sum(1 for r in responses2 if r.get("is_correct", False))
        incorrect = totalReponses - correct
        print("exercices", totalProgress)
        print("totalReponses", totalReponses)
        print("correct", correct)
        print("incorrect", incorrect)
       
       

        return {
            "totalReponses": totalReponses,
            "total_correct": correct,
            "total_incorrect": incorrect,
  
        }

    @staticmethod
    def get_user_competence_summary(db, user_id, subject_id=None):
        """
        Résumé par compétence pour un utilisateur.

        Returns:
            list[dict]: [{competence_id, total, correct, success_rate}, ...]
        """
        collection = db[UserResponse.collection_name]

        match_stage = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id
        }

        # Si subject_id fourni, filtrer les compétences de cette matière
        competence_ids = None
        if subject_id:
            from app.models.competence import Competence
            comps = Competence.get_by_subject(db, subject_id)
            competence_ids = [c["_id"] for c in comps]
            match_stage["competence_id"] = {"$in": competence_ids}

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$competence_id",
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_time": {"$avg": "$time_spent"},
                "last_response": {"$max": "$created_at"},
            }},
            {"$sort": {"last_response": -1}},
        ]

        results = list(collection.aggregate(pipeline))

        summary = []
        for r in results:
            total = r["total"]
            correct = r["correct"]
            summary.append({
                "competence_id": str(r["_id"]),
                "total": total,
                "correct": correct,
                "incorrect": total - correct,
                "success_rate": round(correct / total, 3) if total > 0 else 0.0,
                "avg_time": round(r["avg_time"]) if r["avg_time"] else 0,
                "last_response": r["last_response"],
            })

        return summary

    # ──────────────────────────────────────────────
    # Suppression
    # ──────────────────────────────────────────────

    @staticmethod
    def delete_by_user(db, user_id):
        """Supprime toutes les réponses d'un utilisateur."""
        collection = db[UserResponse.collection_name]
        result = collection.delete_many({
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id
        })
        return result.deleted_count

    @staticmethod
    def delete_by_exercise(db, exercise_id):
        """Supprime toutes les réponses liées à un exercice."""
        collection = db[UserResponse.collection_name]
        result = collection.delete_many({
            "exercise_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id
        })
        return result.deleted_count

    @staticmethod
    def count_by_user(db, user_id, competence_id=None):
        """Compte les réponses d'un utilisateur."""
        collection = db[UserResponse.collection_name]
        query = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id
        }
        if competence_id:
            query["competence_id"] = ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        return collection.count_documents(query)

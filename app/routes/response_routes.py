"""
Routes API pour les réponses utilisateur.
Blueprint : /api/responses

Workflow :
1. Vérifier la réponse
2. ZPD (analyser la zone)
3. SAINT+ (mettre à jour la maîtrise)
4. Sauvegarder la réponse
5. Décision service (simulation LLM)
"""

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.extensions import mongo
from app.models.exercise import Exercise
from app.models.user_response import UserResponse
from app.models.user_progress import UserProgress
from app.schemas.submission_schema import SubmitResponseWithEmotionSchema
from app.services.decision_service import DecisionService
from app.services.saint_service import SAINTService
from app.services.gamification_service import GamificationService
from app.schemas.user_response import SubmitResponseSchema
from app.schemas.user_progress import UserProgressListSchema
from app.services.zpd_service import ZPDService
from bson import ObjectId
import numpy as np

response_bp = Blueprint(
    "responses_final", __name__,
    url_prefix="/api/responses",
    description="Réponses utilisateur"
)
import numpy as np
from bson import ObjectId

def to_jsonable(data):
    if isinstance(data, dict):
        return {k: to_jsonable(v) for k, v in data.items()}
    
    elif isinstance(data, list):
        return [to_jsonable(v) for v in data]
    
    elif isinstance(data, ObjectId):
        return str(data)
    
    elif isinstance(data, (np.floating,)):
        return float(data)
    
    elif isinstance(data, (np.integer,)):
        return int(data)
    
    elif isinstance(data, (np.bool_,)):
        return bool(data)
    
    else:
        return data

@response_bp.route("/submit")
class SubmitResponseWithEmotion(MethodView):

    @response_bp.arguments(SubmitResponseWithEmotionSchema, location='json')
    @response_bp.response(201)
    def post(self, data):
        """
        Workflow :
        1. Vérifier la réponse
        2. ZPD (analyser la zone avec mastery du front)
        3. SAINT+ (mettre à jour la maîtrise)
        4. Sauvegarder la réponse
        5. Décision service (simulation LLM)
        """
        db = mongo.db
        print("execution")
        # ══════════════════════════════════════════════════════════
        # ── 1. DONNÉES DE BASE ──
        # ══════════════════════════════════════════════════════════
        user_id = data.get("user_id")
        exercise_id = data.get("exercise_id")
        competence_id = data.get("competence_id")
        answer = data.get("answer")
        time_spent = data.get("time_spent_seconds", 0)
        hints_used = data.get("hints_used", 0)
        emotion_data = data.get("emotion_data", {})
        
        current_mastery = data.get("current_mastery_level", 0.0)
        
        # ══════════════════════════════════════════════════════════
        # ── 2. VÉRIFIER LA RÉPONSE ──
        # ══════════════════════════════════════════════════════════
        exercise = Exercise.get_by_id(db, exercise_id)
        if not exercise:
            abort(404, message="Exercice non trouvé")
            
        check_result = Exercise.check_answer(exercise, answer)
        is_correct = check_result["is_correct"]
         
        # ══════════════════════════════════════════════════════════
        # ── 3. ZPD (ANALYSE ZONE AVEC MASTERY DU FRONT) ──
        # ══════════════════════════════════════════════════════════
        zpd_result = ZPDService(db).analyze_competence(
            competence_id=str(competence_id),
            mastery_level=current_mastery,
            user_id=user_id,
        )

        print("zpd_result", zpd_result.get("mastery_level"))
        
        # ══════════════════════════════════════════════════════════
        # ── 4. SAINT+ (MISE À JOUR MAÎTRISE) ──
        # ══════════════════════════════════════════════════════════
        
        UserProgress.update_mastery(
            user_id=user_id,
            competence_id=competence_id,
            mastery=float(zpd_result.get("mastery_level")),
            source="saint+"
        )

        print("zpd_result", zpd_result)
        print("mastery_level", zpd_result.get("mastery_level"))
        
        # ══════════════════════════════════════════════════════════
        # ── 5. SAUVEGARDE DE LA RÉPONSE ──
        # ══════════════════════════════════════════════════════════
        # Créer le document de base
        response_doc = UserResponse.create(
            user_id=user_id,
            exercise_id=exercise_id,
            competence_id=competence_id,
            lesson_id=exercise.get("lesson_id"),
            answer=answer,
            is_correct=is_correct,
            time_spent=time_spent
        )
        
        # Ajouter les champs enrichis
        response_doc["hints_used"] = hints_used
        response_doc["emotion_data"] = emotion_data
        response_doc["zpd_result"] = zpd_result
        response_doc["user_id"] = str(user_id)
        response_doc["exercise_id"] = str(exercise_id)
        response_doc["competence_id"] = str(competence_id)
        
        
        # ══════════════════════════════════════════════════════════
        # ── 6. DÉCISION SERVICE (SIMULATION LLM) ──
        # ══════════════════════════════════════════════════════════
        decision = DecisionService.make_decision_with_llm(
            user_id=user_id,
            competence_id=competence_id,
            zpd_result=zpd_result,
            emotion_data=emotion_data,
            is_correct=is_correct,
            time_spent=time_spent,
            hints_used=hints_used,
        )
        
        # decision = DecisionService.make_simple_decision(
        #     zpd_result=zpd_result,
        #     emotion_data=emotion_data,
        #     is_correct=is_correct,
        #     time_spent=time_spent,
        #     hints_used=hints_used,
        # )
        
        # # Mettre à jour le document avec la décision
        db[UserResponse.collection_name].update_one(
            {"_id": response_id},
            {"$set": {"decision": decision}}
        )
        # ══════════════════════════════════════════════════════════
        # ── 7. GAMIFICATION ──
        # ══════════════════════════════════════════════════════════
        stats = UserResponse.get_user_stats(db, user_id, competence_id)
        
        # Attribution des points
        gamification_result = GamificationService.award_points(
            user_id=user_id,
            is_correct=is_correct,
            difficulty=decision.get("recommended_difficulty", 0.5),
            time_spent=time_spent,
            hints_used=hints_used,
            emotion_data=emotion_data
        )
        
        # Vérification des badges
        new_badges = GamificationService.check_and_award_badges(
            user_id=user_id,
            stats=stats,
            mastery_level=float(zpd_result.get("mastery_level", 0))
        )
        
        # Enrichir la réponse avec les données de gamification
        gamification_ui = {
            "xp_earned": gamification_result["xp_earned"],
            "total_xp": gamification_result["total_xp"],
            "level": gamification_result["level"],
            "level_up": gamification_result["level_up"],
            "new_badges": new_badges
        }
        
        # Mettre à jour le message d'encouragement si level up
        if gamification_result["level_up"]:
            decision["encouragement"] = f"🌟 INCROYABLE ! Tu es passé au niveau {gamification_result['level']} ! " + decision.get("encouragement", "")
            decision["ui"]["show_celebration"] = True
            decision["ui"]["encouragement"] = "🌟 INCROYABLE ! Tu es passé au niveau {gamification_result['level']} ! "

        # ══════════════════════════════════════════════════════════
        # ── 8. RÉCOMPENSE MAÎTRISE (PLUS 4) ──
        # ══════════════════════════════════════════════════════════
        # On vérifie si la compétence est maîtrisée (seuil 0.85 par défaut)
        if float(zpd_result.get("mastery_level", 0)) >= 0.85:
            progress = UserProgress.get_or_create(user_id, competence_id)
            if not progress.get("plus4_reward_given", False):
                # Attribution de la carte +4
                reward_res = GamificationServiceV2.attribuer_carte_plus4(user_id, competence_id)
                if reward_res["success"]:
                    # Marquer que la récompense a été donnée
                    mongo.db[UserProgress.COLLECTION].update_one(
                        {"_id": progress["_id"]},
                        {"$set": {"plus4_reward_given": True}}
                    )
                    # Ajouter à l'UI
                    gamification_ui["plus4_earned"] = True
                    decision["encouragement"] = "🏆 MAÎTRISE TOTALE ! Tu as gagné une carte +4 (4 indices gratuits) !" + decision.get("encouragement", "")

        decision["gamification"] = gamification_ui

        # Mettre à jour le document avec la décision finale et gamification
        db[UserResponse.collection_name].update_one(
            {"_id": response_id},
            {"$set": {
                "decision": decision,
                "gamification": gamification_ui
            }}
        )

        # ══════════════════════════════════════════════════════════
        # ── 8. RÉPONSE FINALE ──
        # ══════════════════════════════════════════════════════════
        return to_jsonable(decision), 201


@response_bp.route("/history/<user_id>")
class UserResponseHistory(MethodView):
    """Récupérer l'historique des réponses d'un utilisateur"""
    
    @response_bp.response(200)
    def get(self, user_id):
        db = mongo.db
        
        responses = UserResponse.get_by_user(db, user_id, limit=50)
        
        # Convertir ObjectId en string
        for response in responses:
            response["_id"] = str(response["_id"])
            response["user_id"] = str(response.get("user_id", ""))
            response["exercise_id"] = str(response.get("exercise_id", ""))
            response["competence_id"] = str(response.get("competence_id", ""))
            response["lesson_id"] = str(response.get("lesson_id", ""))
            
        return {
            "user_id": user_id,
            "total_responses": len(responses),
            "responses": responses
        }


@response_bp.route("/stats/<user_id>/<competence_id>")
class CompetenceStats(MethodView):
    """Statistiques pour une compétence donnée"""
    
    @response_bp.response(200)
    def get(self, user_id, competence_id):
        db = mongo.db
        
        # Stats utilisateur pour cette compétence
        stats = UserResponse.get_user_stats(db, user_id, competence_id)
        
        
        return {
            "user_id": user_id,
            "competence_id": competence_id,
            "stats": stats
        }


@response_bp.route("/competence-summary/<user_id>")
class UserCompetenceSummary(MethodView):
    """Résumé de toutes les compétences d'un utilisateur"""
    
    @response_bp.response(200)
    def get(self, user_id):
        db = mongo.db
        
        # Optionnel : filtrer par matière
        subject_id = request.args.get("subject_id")
        
        summary = UserResponse.get_user_competence_summary(db, user_id, subject_id)
        
        # Enrichir avec les données de progression
        for item in summary:
            comp_id = item["competence_id"]
            progress = UserProgress.get_or_create(user_id, comp_id)
            
            item["mastery"] = progress.get("mastery", 0.0)
            item["is_mastered"] = UserProgress.is_mastered(user_id, comp_id)
            item["exercises_completed"] = progress.get("exercises_completed", 0)
            item["source"] = progress.get("source", "saint+")
        
        return {
            "user_id": user_id,
            "subject_id": subject_id,
            "total_competences": len(summary),
            "competences": summary
        }
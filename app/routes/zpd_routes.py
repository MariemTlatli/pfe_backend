"""
Routes API pour l'analyse ZPD — Enrichies avec SAINT+.
"""

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.extensions import mongo
from app.services.zpd_service import ZPDService
from app.schemas.zpd import (
    CompetenceZPDAnalysisSchema,
    SubjectZPDAnalysisSchema,
    ReadyCompetencesSchema,
    NextCompetenceSchema,
    LearningPathSchema
)

import traceback
from flask import jsonify



zpd_bp = Blueprint(
    "zpd", __name__,
    url_prefix="/api/zpd",
    description="Analyse ZPD (enrichie SAINT+)"
)

@zpd_bp.route("/competence/<competence_id>/analyze")
class CompetenceZPDAnalysis(MethodView):
    @zpd_bp.arguments(CompetenceZPDAnalysisSchema, location='json')
    @zpd_bp.response(200)
    def post(self, data, competence_id):
        """Analyse ZPD d'une compétence (enrichie SAINT+ si user_id fourni)."""
        mastery_level = data.get("mastery_level")
        all_masteries = data.get("all_masteries", {})
        user_id = data.get("user_id")  # NOUVEAU : optionnel

        db = mongo.db
        result = ZPDService(db).analyze_competence(
            competence_id, mastery_level, all_masteries, user_id
        )

        if not result:
            abort(404, message=f"Compétence {competence_id} introuvable")
        return result


@zpd_bp.route("/subject/<subject_id>/analyze")
class SubjectZPDAnalysis(MethodView):

    @zpd_bp.arguments(SubjectZPDAnalysisSchema, location='json')
    @zpd_bp.response(200)
    def post(self, data, subject_id):
        """Analyse ZPD complète d'une matière."""
        masteries = data.get("masteries", {})
        user_id = data.get("user_id")  # NOUVEAU

        db = mongo.db
        return ZPDService(db).analyze_subject(subject_id, masteries, user_id)


@zpd_bp.route("/subject/<subject_id>/ready")
class ReadyCompetences(MethodView):

    @zpd_bp.arguments(ReadyCompetencesSchema, location='json')
    @zpd_bp.response(200)
    def post(self, data, subject_id):
        """Compétences prêtes à être travaillées."""
        masteries = data.get("masteries", {})
        user_id = data.get("user_id")  # NOUVEAU

        db = mongo.db
        ready = ZPDService(db).get_ready_competences(subject_id, masteries, user_id)

        return {
            "subject_id": subject_id,
            "ready_count": len(ready),
            "competences": [
                {
                    "competence_id": r["competence_id"],
                    "code": r["code"],
                    "name": r["name"],
                    "mastery_level": r["mastery_level"],
                    "effective_zone": r["effective_zone"],
                    "optimal_difficulty": r["optimal_difficulty"],
                    "recommended_exercise_types": r["recommended_exercise_types"],
                }
                for r in ready
            ],
        }


@zpd_bp.route("/subject/<subject_id>/next")
class NextCompetence(MethodView):

    @zpd_bp.arguments(NextCompetenceSchema, location='json')
    @zpd_bp.response(200)
    def post(self, data, subject_id):
        """Prochaine compétence recommandée."""
        masteries = data.get("masteries", {})
        user_id = data.get("user_id")  # NOUVEAU

        db = mongo.db
        next_comp = ZPDService(db).get_next_competence(subject_id, masteries, user_id)

        if not next_comp:
            return {
                "subject_id": subject_id,
                "message": "Toutes les compétences sont maîtrisées !",
                "next_competence": None,
            }

        return {
            "subject_id": subject_id,
            "next_competence": {
                "competence_id": next_comp["competence_id"],
                "code": next_comp["code"],
                "name": next_comp["name"],
                "mastery_level": next_comp["mastery_level"],
                "effective_zone": next_comp["effective_zone"],
                "zone_label": next_comp["zone_label"],
                "optimal_difficulty": next_comp["optimal_difficulty"],
                "recommended_exercise_types": next_comp["recommended_exercise_types"],
                "is_ready": next_comp["is_ready"],
            },
        }


@zpd_bp.route("/subject/<subject_id>/learning-path")
class LearningPathZPD(MethodView):

    @zpd_bp.arguments(LearningPathSchema, location='json')
    @zpd_bp.response(200)
    def post(self, data, subject_id):
        """Parcours d'apprentissage complet avec ZPD."""
        masteries = data.get("masteries", {})
        user_id = data.get("user_id")  # NOUVEAU

        db = mongo.db
        path = ZPDService(db).get_learning_path_with_zpd(
            subject_id, masteries, user_id
        )

        return {
            "subject_id": subject_id,
            "total_steps": len(path),
            "completed_steps": sum(1 for s in path if s["status"] == "completed"),
            "current_steps": [s for s in path if s["status"] == "current"],
            "path": path,
        }
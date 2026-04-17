"""
Service d'analyse ZPD — Utilise SAINT+ pour la maîtrise.
"""

from bson import ObjectId
from app.models.competence import Competence
from app.models.user_progress import UserProgress
from app.services.saint_service import SAINTService
import logging
import traceback
from flask import jsonify

# Configurer le logger
logger = logging.getLogger("ZPD_DEBUG")
logger.setLevel(logging.DEBUG)

# Handler console avec format détaillé
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "\n{'='*60}\n"
    "[%(asctime)s] %(levelname)s - %(name)s\n"
    "%(message)s\n"
    "{'='*60}"
))
logger.addHandler(handler)

class ZPDService:

    PREREQ_MASTERY_THRESHOLD = 0.70

    ZONE_PRIORITY = {
        Competence.ZONE_ZPD: 0,
        Competence.ZONE_FRUSTRATION: 1,
        Competence.ZONE_MASTERED: 2,
    }

    def __init__(self, db):
        self.db = db

    # ──────────────────────────────────────────────
    # Analyse par compétence (enrichie SAINT+)
    # ──────────────────────────────────────────────

    def analyze_competence(self, competence_id, mastery_level,
                            all_masteries=None, user_id=None):
        """
        Analyse ZPD d'une compétence.
        Si user_id est fourni, on utilise SAINT+ pour une prédiction
        enrichie. Sinon, on utilise le mastery_level fourni.
        """

        competence = Competence.get_by_id(competence_id)
        if not competence:
            return None

        comp_id_str = str(competence["_id"])
        thresholds = competence.get("zpd_thresholds", Competence.DEFAULT_ZPD_THRESHOLDS)
        diff_params = competence.get("difficulty_params", Competence.DEFAULT_DIFFICULTY_PARAMS)

        # Si user_id fourni → prédiction SAINT+ enrichie
        saint_prediction = None
        if user_id and SAINTService.is_loaded():
            saint_prediction = SAINTService.predict(self.db, user_id, competence_id)
            mastery_level = saint_prediction.get("mastery", mastery_level)

        zone = Competence.classify_zone(mastery_level, thresholds)
        
        optimal_difficulty = Competence.get_optimal_difficulty(mastery_level, diff_params)
        exercise_types = Competence.get_exercise_types(mastery_level, thresholds)

        prereq_analysis = self._analyze_prerequisites(competence, all_masteries or {})
        is_ready = prereq_analysis["all_satisfied"]

        effective_zone = zone
        if not is_ready and zone != Competence.ZONE_MASTERED:
            effective_zone = Competence.ZONE_FRUSTRATION

        priority_score = self._compute_priority_score(
            zone=effective_zone,
            mastery=mastery_level,
            prereq_score=prereq_analysis["global_score"],
            level=competence.get("level", 0),
            weight=diff_params.get("weight", 1.0)
        )

        result = {
            "competence_id": comp_id_str,
            "code": competence["code"],
            "name": competence["name"],
            "description": competence.get("description", ""),
            "level": competence.get("level", 0),
            "mastery_level": float(mastery_level),
            "raw_zone": zone,
            "effective_zone": effective_zone,
            "zone_label": self._zone_label(effective_zone),
            "optimal_difficulty": optimal_difficulty,
            "recommended_exercise_types": exercise_types,
            "prerequisites": prereq_analysis,
            "is_ready": is_ready,
            "thresholds": thresholds,
            "difficulty_params": diff_params,
            "priority_score": priority_score,
        }

        # Ajouter les métriques SAINT+ si disponibles
        if saint_prediction:
            result["saint_metrics"] = {
                "p_correct": saint_prediction.get("p_correct"),
                "engagement": saint_prediction.get("engagement"),
                "hint_probability": saint_prediction.get("hint_probability"),
                # "estimated_attempts": saint_prediction.get("estimated_attempts"),
                "anomaly": saint_prediction.get("anomaly"),
                "confidence": saint_prediction.get("confidence"),
            }

        return result

    # ──────────────────────────────────────────────
    # Analyse par matière (enrichie SAINT+)
    # ──────────────────────────────────────────────

    def analyze_subject(self, subject_id, masteries, user_id=None):
        """
        Analyse ZPD complète d'une matière.

        Si user_id fourni → utilise les maîtrises depuis UserProgress
        Sinon → utilise le dict masteries fourni
        """
        competences = Competence.get_by_subject(self.db, subject_id)
        if not competences:
            return {
                "subject_id": str(subject_id),
                "total_competences": 0,
                "competences": [],
                "zones_summary": {"mastered": [], "zpd": [], "frustration": []},
                "zones_count": {"mastered": 0, "zpd": 0, "frustration": 0},
                "recommended_next": [],
                "global_progress": 0.0,
                "stats": {},
            }

        # Si user_id fourni, récupérer les maîtrises depuis la base
        if user_id and not masteries:
            masteries = UserProgress.get_all_masteries(user_id, subject_id)

        analyses = []
        for comp in competences:
            comp_id_str = str(comp["_id"])
            mastery = masteries.get(comp_id_str, 0.0)
            analysis = self.analyze_competence(
                comp["_id"], mastery, masteries, user_id
            )
            if analysis:
                analyses.append(analysis)

        analyses.sort(key=lambda a: a["priority_score"])

        zones_summary = {
            Competence.ZONE_MASTERED: [],
            Competence.ZONE_ZPD: [],
            Competence.ZONE_FRUSTRATION: [],
        }
        for a in analyses:
            zones_summary[a["effective_zone"]].append({
                "competence_id": a["competence_id"],
                "code": a["code"],
                "name": a["name"],
                "mastery_level": a["mastery_level"],
            })

        recommended = [
            a for a in analyses
            if a["effective_zone"] == Competence.ZONE_ZPD and a["is_ready"]
        ]
        if not recommended:
            recommended = [
                a for a in analyses
                if a["effective_zone"] == Competence.ZONE_FRUSTRATION and a["is_ready"]
            ]
        recommended = recommended[:3]

        total = len(analyses)
        mastered_count = len(zones_summary[Competence.ZONE_MASTERED])
        global_progress = round(mastered_count / total, 3) if total > 0 else 0.0

        avg_mastery = 0.0
        if analyses:
            avg_mastery = round(
                sum(a["mastery_level"] for a in analyses) / len(analyses), 3
            )

        return {
            "subject_id": str(subject_id),
            "total_competences": total,
            "competences": analyses,
            "zones_summary": {
                "mastered": zones_summary[Competence.ZONE_MASTERED],
                "zpd": zones_summary[Competence.ZONE_ZPD],
                "frustration": zones_summary[Competence.ZONE_FRUSTRATION],
            },
            "zones_count": {
                "mastered": mastered_count,
                "zpd": len(zones_summary[Competence.ZONE_ZPD]),
                "frustration": len(zones_summary[Competence.ZONE_FRUSTRATION]),
            },
            "recommended_next": [
                {
                    "competence_id": r["competence_id"],
                    "code": r["code"],
                    "name": r["name"],
                    "mastery_level": r["mastery_level"],
                    "optimal_difficulty": r["optimal_difficulty"],
                    "recommended_exercise_types": r["recommended_exercise_types"],
                }
                for r in recommended
            ],
            "global_progress": global_progress,
            "stats": {
                "average_mastery": avg_mastery,
                "mastered_count": mastered_count,
                "in_progress_count": len(zones_summary[Competence.ZONE_ZPD]),
                "not_started_count": len(zones_summary[Competence.ZONE_FRUSTRATION]),
            },
        }

    # ──────────────────────────────────────────────
    # Compétences prêtes
    # ──────────────────────────────────────────────

    def get_ready_competences(self, subject_id, masteries, user_id=None):
        analysis = self.analyze_subject(subject_id, masteries, user_id)
        return [
            comp for comp in analysis["competences"]
            if comp["is_ready"] and comp["effective_zone"] != Competence.ZONE_MASTERED
        ]

    def get_next_competence(self, subject_id, masteries, user_id=None):
        ready = self.get_ready_competences(subject_id, masteries, user_id)
        return ready[0] if ready else None

    # ──────────────────────────────────────────────
    # Prérequis (inchangé)
    # ──────────────────────────────────────────────

    def _analyze_prerequisites(self, competence, all_masteries):
        prereqs = competence.get("prerequisites", [])
        if not prereqs:
            return {"count": 0, "details": [], "all_satisfied": True, "global_score": 1.0}

        details = []
        scores = []

        for prereq in prereqs:
            prereq_id = prereq["competence_id"]
            prereq_id_str = str(prereq_id)
            strength = prereq.get("strength", 1.0)

            prereq_comp = Competence.get_by_id(prereq_id)
            if not prereq_comp:
                continue

            mastery = all_masteries.get(prereq_id_str, 0.0)
            weighted_score = (strength * mastery) + ((1 - strength) * 1.0)
            satisfied = weighted_score >= self.PREREQ_MASTERY_THRESHOLD

            details.append({
                "competence_id": prereq_id_str,
                "code": prereq_comp["code"],
                "name": prereq_comp["name"],
                "strength": strength,
                "mastery": mastery,
                "weighted_score": round(weighted_score, 3),
                "satisfied": satisfied,
            })
            scores.append(weighted_score)

        all_satisfied = all(d["satisfied"] for d in details) if details else True
        global_score = round(sum(scores) / len(scores), 3) if scores else 1.0

        return {
            "count": len(details),
            "details": details,
            "all_satisfied": all_satisfied,
            "global_score": global_score,
        }

    def _compute_priority_score(self, zone, mastery, prereq_score, level, weight):
        zone_base = self.ZONE_PRIORITY.get(zone, 1) * 100
        prereq_bonus = (1.0 - prereq_score) * 30
        level_bonus = level * 5
        mastery_bonus = 0
        if zone == Competence.ZONE_ZPD:
            mastery_bonus = mastery * 20
        weight_factor = 1.0 / max(weight, 0.1)
        score = (zone_base + prereq_bonus + level_bonus + mastery_bonus) * weight_factor
        return round(score, 2)

    # ──────────────────────────────────────────────
    # Learning path (inchangé)
    # ──────────────────────────────────────────────

    def get_learning_path_with_zpd(self, subject_id, masteries, user_id=None):
        competences = Competence.get_by_subject(self.db, subject_id)
        if not competences:
            return []

        if user_id and not masteries:
            masteries = UserProgress.get_all_masteries(user_id, subject_id)

        analyses = []
        for comp in competences:
            comp_id_str = str(comp["_id"])
            mastery = masteries.get(comp_id_str, 0.0)
            analysis = self.analyze_competence(comp["_id"], mastery, masteries, user_id)
            if analysis:
                analyses.append(analysis)

        analyses.sort(key=lambda a: (a["level"], a["priority_score"]))

        path = []
        for i, a in enumerate(analyses):
            path.append({
                "step": i + 1,
                "competence_id": a["competence_id"],
                "code": a["code"],
                "name": a["name"],
                "level": a["level"],
                "mastery_level": a["mastery_level"],
                "zone": a["effective_zone"],
                "zone_label": a["zone_label"],
                "is_ready": a["is_ready"],
                "optimal_difficulty": a["optimal_difficulty"],
                "status": self._step_status(a),
            })
        return path

    @staticmethod
    def _step_status(analysis):
        if analysis["effective_zone"] == Competence.ZONE_MASTERED:
            return "completed"
        elif analysis["is_ready"] and analysis["effective_zone"] == Competence.ZONE_ZPD:
            return "current"
        elif analysis["is_ready"]:
            return "available"
        else:
            return "locked"

    @staticmethod
    def _zone_label(zone):
        labels = {
            Competence.ZONE_MASTERED: "Maîtrisé — Prêt pour la suite",
            Competence.ZONE_ZPD: "Zone Proximale — Apprentissage optimal",
            Competence.ZONE_FRUSTRATION: "Zone de Frustration — Renforcer les bases",
        }
        return labels.get(zone, "Inconnu")
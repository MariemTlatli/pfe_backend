"""
Création des fichiers pour l'étape 2 (ZPD Service).
Usage : python scripts/setup_step2.py
"""

import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def create_file(relative_path, content):
    full_path = os.path.join(ROOT, relative_path)
    directory = os.path.dirname(full_path)

    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"  📁 Dossier créé : {directory}")

    if os.path.exists(full_path):
        print(f"  ⚠️  EXISTE DÉJÀ : {relative_path}")
        return False

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ Créé : {relative_path}")
    return True


# ══════════════════════════════════════════════
# zpd_service.py
# ══════════════════════════════════════════════

ZPD_SERVICE = '''"""
Service d\'analyse ZPD (Zone Proximale de Développement).
"""

from bson import ObjectId
from app.models.competence import Competence


class ZPDService:

    PREREQ_MASTERY_THRESHOLD = 0.70

    ZONE_PRIORITY = {
        Competence.ZONE_ZPD: 0,
        Competence.ZONE_FRUSTRATION: 1,
        Competence.ZONE_MASTERED: 2,
    }

    def __init__(self, db):
        self.db = db

    def analyze_competence(self, competence_id, mastery_level, all_masteries=None):
        competence = Competence.get_by_id(self.db, competence_id)
        if not competence:
            return None

        comp_id_str = str(competence["_id"])
        thresholds = competence.get("zpd_thresholds", Competence.DEFAULT_ZPD_THRESHOLDS)
        diff_params = competence.get("difficulty_params", Competence.DEFAULT_DIFFICULTY_PARAMS)

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

        return {
            "competence_id": comp_id_str,
            "code": competence["code"],
            "name": competence["name"],
            "description": competence.get("description", ""),
            "level": competence.get("level", 0),
            "mastery_level": mastery_level,
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

    def analyze_subject(self, subject_id, masteries):
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

        analyses = []
        for comp in competences:
            comp_id_str = str(comp["_id"])
            mastery = masteries.get(comp_id_str, 0.0)
            analysis = self.analyze_competence(comp["_id"], mastery, masteries)
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
            avg_mastery = round(sum(a["mastery_level"] for a in analyses) / len(analyses), 3)

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

    def get_ready_competences(self, subject_id, masteries):
        analysis = self.analyze_subject(subject_id, masteries)
        return [
            comp for comp in analysis["competences"]
            if comp["is_ready"] and comp["effective_zone"] != Competence.ZONE_MASTERED
        ]

    def get_next_competence(self, subject_id, masteries):
        ready = self.get_ready_competences(subject_id, masteries)
        return ready[0] if ready else None

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

            prereq_comp = Competence.get_by_id(self.db, prereq_id)
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

    def get_learning_path_with_zpd(self, subject_id, masteries):
        competences = Competence.get_by_subject(self.db, subject_id)
        if not competences:
            return []

        analyses = []
        for comp in competences:
            comp_id_str = str(comp["_id"])
            mastery = masteries.get(comp_id_str, 0.0)
            analysis = self.analyze_competence(comp["_id"], mastery, masteries)
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
'''

# ══════════════════════════════════════════════
# zpd_routes.py
# ══════════════════════════════════════════════

ZPD_ROUTES = '''"""
Routes API pour l\'analyse ZPD.
"""

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.extensions import get_db
from app.services.zpd_service import ZPDService

zpd_bp = Blueprint(
    "zpd", __name__,
    url_prefix="/api/zpd",
    description="Analyse ZPD"
)


@zpd_bp.route("/competence/<competence_id>/analyze")
class CompetenceZPDAnalysis(MethodView):

    @zpd_bp.response(200)
    def post(self, competence_id):
        data = request.get_json() or {}
        mastery_level = data.get("mastery_level")

        if mastery_level is None:
            abort(400, message="mastery_level requis")

        try:
            mastery_level = float(mastery_level)
        except (ValueError, TypeError):
            abort(400, message="mastery_level doit être un nombre")

        if not 0.0 <= mastery_level <= 1.0:
            abort(400, message="mastery_level entre 0.0 et 1.0")

        all_masteries = data.get("all_masteries", {})

        db = get_db()
        result = ZPDService(db).analyze_competence(competence_id, mastery_level, all_masteries)

        if not result:
            abort(404, message=f"Compétence {competence_id} introuvable")
        return result


@zpd_bp.route("/subject/<subject_id>/analyze")
class SubjectZPDAnalysis(MethodView):

    @zpd_bp.response(200)
    def post(self, subject_id):
        data = request.get_json() or {}
        masteries = data.get("masteries", {})

        for key, val in masteries.items():
            try:
                masteries[key] = float(val)
            except (ValueError, TypeError):
                abort(400, message=f"Maîtrise invalide pour {key}")

        db = get_db()
        return ZPDService(db).analyze_subject(subject_id, masteries)


@zpd_bp.route("/subject/<subject_id>/ready")
class ReadyCompetences(MethodView):

    @zpd_bp.response(200)
    def post(self, subject_id):
        data = request.get_json() or {}
        masteries = data.get("masteries", {})

        db = get_db()
        ready = ZPDService(db).get_ready_competences(subject_id, masteries)

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

    @zpd_bp.response(200)
    def post(self, subject_id):
        data = request.get_json() or {}
        masteries = data.get("masteries", {})

        db = get_db()
        next_comp = ZPDService(db).get_next_competence(subject_id, masteries)

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

    @zpd_bp.response(200)
    def post(self, subject_id):
        data = request.get_json() or {}
        masteries = data.get("masteries", {})

        db = get_db()
        path = ZPDService(db).get_learning_path_with_zpd(subject_id, masteries)

        return {
            "subject_id": subject_id,
            "total_steps": len(path),
            "completed_steps": sum(1 for s in path if s["status"] == "completed"),
            "current_steps": [s for s in path if s["status"] == "current"],
            "path": path,
        }
'''

# ══════════════════════════════════════════════
# CRÉATION
# ══════════════════════════════════════════════

FILES = {
    "app/services/zpd_service.py": ZPD_SERVICE,
    "app/routes/zpd_routes.py": ZPD_ROUTES,
}


def main():
    print("=" * 50)
    print("  SETUP ÉTAPE 2 : ZPD Service")
    print("=" * 50)
    print(f"  Racine : {ROOT}\n")

    created = 0
    skipped = 0

    for path, content in FILES.items():
        if create_file(path, content):
            created += 1
        else:
            skipped += 1

    print(f"\n  Créés  : {created}")
    print(f"  Ignorés: {skipped}")

    print(f"\n  ⚠️  Ajouter dans app/__init__.py :")
    print(f"     from app.routes.zpd_routes import zpd_bp")
    print(f"     api.register_blueprint(zpd_bp)")


if __name__ == "__main__":
    main()
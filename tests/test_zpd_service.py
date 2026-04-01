"""
Tests unitaires pour ZPDService.
Usage : python -m pytest tests/test_zpd_service.py -v

Utilise une base de test MongoDB.
"""

import pytest
from pymongo import MongoClient
from bson import ObjectId
from app.models.competence import Competence
from app.services.zpd_service import ZPDService


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def db():
    """Base de test isolée, nettoyée après chaque test."""
    client = MongoClient("mongodb://localhost:27017")
    test_db = client["test_zpd_service"]
    yield test_db
    # Cleanup
    client.drop_database("test_zpd_service")


@pytest.fixture
def subject_id():
    return ObjectId()


@pytest.fixture
def sample_competences(db, subject_id):
    """
    Crée un graphe de compétences de test :

        BAS001 (level 0) ──→ VAR001 (level 1) ──→ COND001 (level 2)
                                                ──→ LOOP001 (level 2)
                                                        ──→ FUNC001 (level 3)
    """
    collection = db[Competence.collection_name]

    # Créer les compétences
    comps = {}

    for code, name, level in [
        ("BAS001", "Syntaxe de base", 0),
        ("VAR001", "Variables et types", 1),
        ("COND001", "Conditions", 2),
        ("LOOP001", "Boucles", 2),
        ("FUNC001", "Fonctions", 3),
    ]:
        doc = Competence.create(
            subject_id=subject_id,
            code=code,
            name=name,
            description=f"Description de {name}",
            level=level,
            difficulty_params={
                "base_difficulty": 0.3 + level * 0.15,
                "weight": 1.0,
                "min_exercises": 3,
                "mastery_exercises": 5,
            }
        )
        result = collection.insert_one(doc)
        comps[code] = str(result.inserted_id)

    # Ajouter les prérequis
    # VAR001 ← BAS001
    Competence.add_prerequisite(db, comps["VAR001"], comps["BAS001"], strength=1.0)
    # COND001 ← VAR001
    Competence.add_prerequisite(db, comps["COND001"], comps["VAR001"], strength=1.0)
    # LOOP001 ← VAR001
    Competence.add_prerequisite(db, comps["LOOP001"], comps["VAR001"], strength=0.8)
    # FUNC001 ← LOOP001
    Competence.add_prerequisite(db, comps["FUNC001"], comps["LOOP001"], strength=1.0)

    return comps


@pytest.fixture
def zpd_service(db):
    return ZPDService(db)


# ──────────────────────────────────────────────
# Tests : analyse d'une compétence
# ──────────────────────────────────────────────

class TestAnalyzeCompetence:

    def test_basic_analysis(self, zpd_service, sample_competences):
        """Analyse basique sans prérequis (compétence racine)."""
        result = zpd_service.analyze_competence(
            sample_competences["BAS001"],
            mastery_level=0.55
        )

        assert result is not None
        assert result["code"] == "BAS001"
        assert result["mastery_level"] == 0.55
        assert result["effective_zone"] == Competence.ZONE_ZPD
        assert result["is_ready"] is True  # Pas de prérequis
        assert "recommended_exercise_types" in result

    def test_mastered_competence(self, zpd_service, sample_competences):
        """Compétence maîtrisée."""
        result = zpd_service.analyze_competence(
            sample_competences["BAS001"],
            mastery_level=0.90
        )
        assert result["effective_zone"] == Competence.ZONE_MASTERED

    def test_frustration_zone(self, zpd_service, sample_competences):
        """Compétence en zone de frustration."""
        result = zpd_service.analyze_competence(
            sample_competences["BAS001"],
            mastery_level=0.15
        )
        assert result["effective_zone"] == Competence.ZONE_FRUSTRATION

    def test_not_ready_prereqs_not_met(self, zpd_service, sample_competences):
        """Compétence avec prérequis non satisfaits → pas prête."""
        # VAR001 nécessite BAS001, mais BAS001 a mastery=0.20
        result = zpd_service.analyze_competence(
            sample_competences["VAR001"],
            mastery_level=0.50,
            all_masteries={sample_competences["BAS001"]: 0.20}
        )
        assert result["is_ready"] is False
        assert result["effective_zone"] == Competence.ZONE_FRUSTRATION

    def test_ready_prereqs_met(self, zpd_service, sample_competences):
        """Compétence avec prérequis satisfaits → prête."""
        result = zpd_service.analyze_competence(
            sample_competences["VAR001"],
            mastery_level=0.50,
            all_masteries={sample_competences["BAS001"]: 0.85}
        )
        assert result["is_ready"] is True
        assert result["effective_zone"] == Competence.ZONE_ZPD

    def test_weak_prerequisite_easier(self, zpd_service, sample_competences):
        """Prérequis faible (strength=0.5) → plus facile à satisfaire."""
        # LOOP001 ← VAR001 avec strength=0.8
        # Avec VAR001 mastery=0.65 :
        # weighted = 0.8*0.65 + 0.2*1.0 = 0.72 ≥ 0.70 → satisfait
        result = zpd_service.analyze_competence(
            sample_competences["LOOP001"],
            mastery_level=0.50,
            all_masteries={sample_competences["VAR001"]: 0.65}
        )
        assert result["prerequisites"]["details"][0]["satisfied"] is True

    def test_nonexistent_competence(self, zpd_service):
        """Compétence inexistante → None."""
        result = zpd_service.analyze_competence(
            str(ObjectId()),
            mastery_level=0.50
        )
        assert result is None


# ──────────────────────────────────────────────
# Tests : analyse d'une matière complète
# ──────────────────────────────────────────────

class TestAnalyzeSubject:

    def test_all_zero_mastery(self, zpd_service, sample_competences, subject_id):
        """Tout à 0 → tout en frustration, seul BAS001 est ready."""
        result = zpd_service.analyze_subject(str(subject_id), {})

        assert result["total_competences"] == 5
        assert result["global_progress"] == 0.0
        assert result["zones_count"]["frustration"] == 5

        # Seul BAS001 (pas de prérequis) devrait être recommandé
        recommended = result["recommended_next"]
        assert len(recommended) >= 1
        codes = [r["code"] for r in recommended]
        assert "BAS001" in codes

    def test_partial_mastery(self, zpd_service, sample_competences, subject_id):
        """Progression partielle → mix de zones."""
        masteries = {
            sample_competences["BAS001"]: 0.90,   # maîtrisé
            sample_competences["VAR001"]: 0.55,    # ZPD
            sample_competences["COND001"]: 0.10,   # frustration
            sample_competences["LOOP001"]: 0.10,   # frustration
            # FUNC001 absent → 0.0
        }

        result = zpd_service.analyze_subject(str(subject_id), masteries)

        assert result["zones_count"]["mastered"] == 1   # BAS001
        assert result["global_progress"] > 0.0
        assert result["stats"]["average_mastery"] > 0.0

    def test_all_mastered(self, zpd_service, sample_competences, subject_id):
        """Tout maîtrisé → progress = 100%."""
        masteries = {v: 0.95 for v in sample_competences.values()}

        result = zpd_service.analyze_subject(str(subject_id), masteries)

        assert result["global_progress"] == 1.0
        assert result["zones_count"]["mastered"] == 5
        assert result["recommended_next"] == []

    def test_empty_subject(self, zpd_service):
        """Matière sans compétences."""
        result = zpd_service.analyze_subject(str(ObjectId()), {})
        assert result["total_competences"] == 0


# ──────────────────────────────────────────────
# Tests : next competence
# ──────────────────────────────────────────────

class TestNextCompetence:

    def test_fresh_start(self, zpd_service, sample_competences, subject_id):
        """Début → recommander BAS001 (racine)."""
        result = zpd_service.get_next_competence(str(subject_id), {})
        assert result is not None
        assert result["code"] == "BAS001"

    def test_after_first_mastered(self, zpd_service, sample_competences, subject_id):
        """BAS001 maîtrisé → recommander VAR001."""
        masteries = {sample_competences["BAS001"]: 0.90}
        result = zpd_service.get_next_competence(str(subject_id), masteries)
        assert result is not None
        assert result["code"] == "VAR001"

    def test_all_done(self, zpd_service, sample_competences, subject_id):
        """Tout maîtrisé → None."""
        masteries = {v: 0.95 for v in sample_competences.values()}
        result = zpd_service.get_next_competence(str(subject_id), masteries)
        assert result is None


# ──────────────────────────────────────────────
# Tests : learning path
# ──────────────────────────────────────────────

class TestLearningPath:

    def test_path_order(self, zpd_service, sample_competences, subject_id):
        """Le parcours respecte l'ordre topologique (levels croissants)."""
        path = zpd_service.get_learning_path_with_zpd(str(subject_id), {})

        assert len(path) == 5
        levels = [step["level"] for step in path]
        assert levels == sorted(levels)

    def test_path_statuses(self, zpd_service, sample_competences, subject_id):
        """Vérifier les statuts du parcours."""
        masteries = {
            sample_competences["BAS001"]: 0.90,
            sample_competences["VAR001"]: 0.55,
        }
        path = zpd_service.get_learning_path_with_zpd(str(subject_id), masteries)

        statuses = {step["code"]: step["status"] for step in path}
        assert statuses["BAS001"] == "completed"
        assert statuses["VAR001"] == "current"  # ZPD + ready


# ──────────────────────────────────────────────
# Tests : prerequisite analysis
# ──────────────────────────────────────────────

class TestPrerequisiteAnalysis:

    def test_no_prereqs(self, zpd_service, sample_competences):
        """Compétence sans prérequis → score 1.0, all_satisfied True."""
        result = zpd_service.analyze_competence(
            sample_competences["BAS001"], 0.50
        )
        assert result["prerequisites"]["count"] == 0
        assert result["prerequisites"]["all_satisfied"] is True
        assert result["prerequisites"]["global_score"] == 1.0

    def test_prereq_details(self, zpd_service, sample_competences):
        """Vérifier les détails des prérequis."""
        result = zpd_service.analyze_competence(
            sample_competences["VAR001"],
            mastery_level=0.50,
            all_masteries={sample_competences["BAS001"]: 0.60}
        )
        prereqs = result["prerequisites"]
        assert prereqs["count"] == 1
        assert prereqs["details"][0]["code"] == "BAS001"
        assert prereqs["details"][0]["mastery"] == 0.60
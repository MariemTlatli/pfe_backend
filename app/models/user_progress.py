"""
Modèle UserProgress — Suivi de progression avec SAINT+.
Remplace l'ancien système BKT.
"""

from app.extensions import mongo
from bson import ObjectId
from datetime import datetime
from app.config import Config


class UserProgress:
    """Gestion du suivi de progression (SAINT+)."""

    COLLECTION = 'user_progress'

    # ──────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────

    @staticmethod
    def get_or_create(user_id, competence_id , difficulty=0.5):
        """
        Récupérer ou créer le progrès d'un utilisateur pour une compétence.
        """
        progress = mongo.db[UserProgress.COLLECTION].find_one({
            'user_id': user_id,
            'competence_id': ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        })

        if not progress:
            progress = {
                'user_id': user_id,
                'competence_id': ObjectId(competence_id) if isinstance(competence_id, str) else competence_id,
                'mastery': 0.0,
                'source': 'saint+',
                'exercises_completed': 0,
                'last_attempt': None,
                'last_prediction': None,    # Dernière prédiction SAINT+ complète
                'difficulty': difficulty,
                'plus4_reward_given': False
            }
            result = mongo.db[UserProgress.COLLECTION].insert_one(progress)
            progress['_id'] = result.inserted_id

        return progress

    @staticmethod
    def find_by_user(user_id):
        """Récupérer toutes les progressions d'un utilisateur."""
        return list(mongo.db[UserProgress.COLLECTION].find({'user_id': user_id}))

    @staticmethod
    def find_by_user_and_subject(user_id, subject_id):
        """Récupérer les progressions d'un utilisateur pour une matière."""
        from app.models.competence import Competence

        competences = Competence.find_by_subject(subject_id)
        competence_ids = [comp['_id'] for comp in competences]

        return list(mongo.db[UserProgress.COLLECTION].find({
            'user_id': user_id,
            'competence_id': {'$in': competence_ids}
        }))

    # ──────────────────────────────────────────────
    # Mise à jour depuis SAINT+
    # ──────────────────────────────────────────────

    @staticmethod
    def update_mastery(user_id, competence_id, mastery, source="saint+",
                       prediction_details=None):
        """
        Met à jour la maîtrise après une prédiction SAINT+.

        Args:
            user_id: ID utilisateur
            competence_id: ID compétence
            mastery: float [0, 1] — score de maîtrise
            source: str — "saint+" ou "fallback"
            prediction_details: dict — résultat enrichi complet (optionnel)
        """
        update_data = {
            'mastery': mastery,
            'source': source,
            'updated_at': datetime.utcnow()
        }

        if prediction_details:
            # Stocker les métriques enrichies pour consultation ultérieure
            update_data['last_prediction'] = {
                'p_correct': prediction_details.get('p_correct'),
                'zone': prediction_details.get('zone'),
                'engagement': prediction_details.get('engagement', {}).get('score'),
                'hint_probability': prediction_details.get('hint_probability', {}).get('probability'),
                'anomaly_detected': prediction_details.get('anomaly', {}).get('has_anomaly', False),
                'confidence': prediction_details.get('confidence', {}).get('level'),
                'timestamp': datetime.utcnow()
            }

        mongo.db[UserProgress.COLLECTION].update_one(
            {
                'user_id': user_id,
                'competence_id': ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
            },
            {
                '$set': update_data,
                '$inc': {'exercises_completed': 1},
                '$currentDate': {'last_attempt': True}
            },
            upsert=True
        )

    # ──────────────────────────────────────────────
    # Lecture de la maîtrise
    # ──────────────────────────────────────────────

    @staticmethod
    def get_mastery_level(user_id, competence_id):
        """Récupérer le niveau de maîtrise d'une compétence."""
        progress = UserProgress.get_or_create(user_id, competence_id)
        return progress.get('mastery', 0.0)

    @staticmethod
    def is_mastered(user_id, competence_id, threshold=None):
        """Vérifier si une compétence est maîtrisée."""
        if threshold is None:
            threshold = Config.SAINT_MASTERY_THRESHOLD
        mastery = UserProgress.get_mastery_level(user_id, competence_id)
        return mastery >= threshold

    @staticmethod
    def get_all_masteries(user_id, subject_id=None):
        """
        Récupère toutes les maîtrises d'un utilisateur.

        Returns:
            dict: {competence_id_str: mastery_float, ...}
        """
        if subject_id:
            progresses = UserProgress.find_by_user_and_subject(user_id, subject_id)
        else:
            progresses = UserProgress.find_by_user(user_id)

        return {
            str(p['competence_id']): p.get('mastery', 0.0)
            for p in progresses
        }

    @staticmethod
    def get_last_prediction(user_id, competence_id):
        """Récupère la dernière prédiction SAINT+ complète."""
        progress = UserProgress.get_or_create(user_id, competence_id)
        return progress.get('last_prediction')

    # ──────────────────────────────────────────────
    # Prochaine compétence
    # ──────────────────────────────────────────────

    @staticmethod
    def get_next_competence(user_id, subject_id):
        """
        Déterminer la prochaine compétence à étudier.
        Utilise la maîtrise SAINT+ + prérequis.
        """
        from app.models.competence import Competence

        competences = Competence.find_by_subject(subject_id)

        for comp in sorted(competences, key=lambda x: x['level']):
            if UserProgress.is_mastered(user_id, comp['_id']):
                continue

            prerequisites_met = True
            for prereq in comp.get('prerequisites', []):
                if not UserProgress.is_mastered(user_id, prereq['competence_id']):
                    prerequisites_met = False
                    break

            if prerequisites_met:
                return comp

        return None

    # ──────────────────────────────────────────────
    # Sérialisation
    # ──────────────────────────────────────────────

    @staticmethod
    def to_dict(progress):
        """Convertir en dict JSON-friendly."""
        if not progress:
            return None

        result = {
            'id': str(progress['_id']),
            'user_id': progress['user_id'],
            'competence_id': str(progress['competence_id']),
            'mastery': round(progress.get('mastery', 0.0), 4),
            'source': progress.get('source', 'saint+'),
            'exercises_completed': progress.get('exercises_completed', 0),
            'last_attempt': progress['last_attempt'].isoformat()
                if progress.get('last_attempt') else None,
            'updated_at': progress['updated_at'].isoformat()
                if progress.get('updated_at') else None,
            'plus4_reward_given': progress.get('plus4_reward_given', False)
        }

        # Inclure la dernière prédiction si disponible
        last_pred = progress.get('last_prediction')
        if last_pred:
            result['last_prediction'] = {
                'p_correct': last_pred.get('p_correct'),
                'zone': last_pred.get('zone'),
                'engagement': last_pred.get('engagement'),
                'confidence': last_pred.get('confidence'),
                'anomaly_detected': last_pred.get('anomaly_detected', False),
            }

        return result
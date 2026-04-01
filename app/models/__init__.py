"""
Modèles MongoDB pour l'apprentissage adaptatif.
"""

from app.models.domain import Domain
from app.models.subject import Subject
from app.models.competence import Competence
from app.models.lesson import Lesson
from app.models.user_progress import UserProgress
from .emotion_model import emotion_model, EmotionModel

__all__ = [
    'Domain',
    'Subject',
    'Competence',
    'Lesson',
    'UserProgress', 
    'emotion_model', 'EmotionModel'
]
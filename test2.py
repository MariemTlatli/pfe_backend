"""
Génère 10 fichiers JSON de test pour l'API de soumission.

Usage:
    python generate_test_json.py --competence_id <ID> --user_id <ID> --output_dir ./test_data
"""

import sys
import os
import json
import random
import argparse
from datetime import datetime, timedelta
from bson import ObjectId

# Configuration du path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymongo import MongoClient

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════


MONGO_URI = "mongodb+srv://crud:H24ZJZXDzDOoVYKD@cluster0.gjtsy.mongodb.net/"
DB_NAME = "adaptive_learning_db"
mongo = MongoClient(MONGO_URI)

db = mongo[DB_NAME]

print(f"✅ Connecté à MongoDB : {DB_NAME}")

# IDs à personnaliser
DEFAULT_USER_ID = "69bd7281249d4974c7980baf"
DEFAULT_COMPETENCE_ID = "69c0ef05016445716a1344f9"

# Émotions possibles
EMOTIONS = [
    {"emotion": "happy", "frustration": False, "confidence_range": (0.8, 1.0)},
    {"emotion": "focused", "frustration": False, "confidence_range": (0.7, 0.95)},
    {"emotion": "neutral", "frustration": False, "confidence_range": (0.5, 0.8)},
    {"emotion": "confused", "frustration": False, "confidence_range": (0.3, 0.6)},
    {"emotion": "frustrated", "frustration": True, "confidence_range": (0.2, 0.5)},
    {"emotion": "anxious", "frustration": True, "confidence_range": (0.3, 0.6)},
]

# Zones ZPD possibles
ZPD_ZONES = ["frustration", "zpd", "mastered"]


# ═══════════════════════════════════════════════════════════════════
# GÉNÉRATEUR
# ═══════════════════════════════════════════════════════════════════

class TestJSONGenerator:
    """Génère des fichiers JSON de test pour l'API."""
    
    def __init__(self, db, user_id: str, competence_id: str):
        self.db = db
        self.user_id = user_id
        self.competence_id = competence_id
        self.exercises = self._get_exercises()
        self.base_time = datetime.utcnow() - timedelta(hours=10)
    
    def _get_exercises(self) -> list:
        """Récupère les exercices de la compétence."""
        collection = self.db["exercises"]
        exercises = list(collection.find({
            "competence_id": ObjectId(self.competence_id)
        }).limit(10))
        
        print(f"📦 {len(exercises)} exercices trouvés pour la compétence {self.competence_id}")
        return exercises
    
    def _generate_emotion_data(self, is_correct: bool, mastery_level: float) -> dict:
        """Génère des données d'émotion réalistes."""
        
        # Pondération selon la réussite
        if is_correct and mastery_level > 0.7:
            weights = [0.4, 0.3, 0.2, 0.05, 0.03, 0.02]  # Plus de happy/focused
        elif not is_correct or mastery_level < 0.4:
            weights = [0.05, 0.1, 0.15, 0.25, 0.25, 0.2]  # Plus de frustrated/confused
        else:
            weights = [0.15, 0.2, 0.3, 0.15, 0.1, 0.1]  # Équilibré
        
        emotion_choice = random.choices(EMOTIONS, weights=weights, k=1)[0]
        
        confidence = random.uniform(*emotion_choice["confidence_range"])
        
        timestamp = self.base_time.isoformat() + "Z"
        
        return {
            "dominant_emotion": emotion_choice["emotion"],
            "confidence": round(confidence, 2),
            "emotion_history": [
                {
                    "emotion": emotion_choice["emotion"],
                    "confidence": round(confidence, 2),
                    "timestamp": timestamp
                }
            ],
            "frustration_detected": emotion_choice["frustration"],
            "average_confidence": round(confidence, 2)
        }
    
    def _generate_answer(self, exercise: dict, is_correct: bool) -> str:
        """Génère une réponse (correcte ou fausse)."""
        
        if is_correct:
            return exercise.get("answer", "bonne réponse")
        else:
            # Générer une mauvaise réponse
            wrong_answers = exercise.get("wrong_answers", [])
            if wrong_answers:
                return random.choice(wrong_answers)
            else:
                return f"fausse réponse {random.randint(1, 100)}"
    
    def _get_zpd_zone(self, mastery_level: float) -> str:
        """Détermine la zone ZPD selon la maîtrise."""
        if mastery_level < 0.4:
            return "frustration"
        elif mastery_level < 0.85:
            return "zpd"
        else:
            return "mastered"
    
    def generate_test_case(self, index: int, exercise: dict) -> dict:
        """Génère un seul cas de test."""
        
        # Progression de maîtrise simulée (augmente avec le temps)
        base_mastery = 0.3
        mastery_increment = 0.06
        mastery_level = min(0.95, base_mastery + (index * mastery_increment))
        
        # Déterminer si correct (plus de succès vers la fin)
        success_probability = 0.4 + (index * 0.06)
        is_correct = random.random() < success_probability
        
        # Hints (moins vers la fin)
        hints_probability = 0.5 - (index * 0.04)
        hints_used = random.randint(0, 2) if random.random() < hints_probability else 0
        
        # ZPD zone
        zpd_zone = self._get_zpd_zone(mastery_level)
        
        # Émotion
        emotion_data = self._generate_emotion_data(is_correct, mastery_level)
        
        # Timestamp progressif
        timestamp = (self.base_time + timedelta(hours=index)).isoformat() + "Z"
        
        return {
            "user_id": self.user_id,
            "exercise_id": str(exercise["_id"]),
            "competence_id": self.competence_id,
            "answer": self._generate_answer(exercise, is_correct),
            "is_correct": is_correct,
            "hints_used": hints_used,
            "attempt_number": 1,
            "emotion_data": emotion_data,
            "current_zpd_zone": zpd_zone,
            "current_mastery_level": round(mastery_level, 2),
            "time_spent_seconds": random.randint(20, 90),
            "timestamp": timestamp
        }
    
    def generate_all(self, output_dir: str) -> list:
        """Génère tous les fichiers JSON."""
        
        if not self.exercises:
            print("❌ Aucun exercice trouvé !")
            return []
        
        # Créer le dossier
        os.makedirs(output_dir, exist_ok=True)
        
        files_created = []
        
        for i, exercise in enumerate(self.exercises[:10], 1):
            test_case = self.generate_test_case(i, exercise)
            
            # Nom du fichier
            filename = f"test_submission_{i:02d}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Sauvegarder
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(test_case, f, indent=2, ensure_ascii=False)
            
            files_created.append(filepath)
            
            print(f"✅ {filename} généré")
            print(f"    Exercise: {exercise.get('code', 'N/A')}")
            print(f"    Correct: {test_case['is_correct']}")
            print(f"    Mastery: {test_case['current_mastery_level']}")
            print(f"    Zone: {test_case['current_zpd_zone']}")
            print(f"    Emotion: {test_case['emotion_data']['dominant_emotion']}")
        
        # Générer un fichier unique avec tous les tests
        all_tests_file = os.path.join(output_dir, "all_test_submissions.json")
        with open(all_tests_file, 'w', encoding='utf-8') as f:
            json.dump({
                "total": len(files_created),
                "user_id": self.user_id,
                "competence_id": self.competence_id,
                "test_cases": [self.generate_test_case(i, ex) for i, ex in enumerate(self.exercises[:10], 1)]
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Fichier consolidé: {all_tests_file}")
        
        return files_created


# ═══════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Génère des JSON de test")
    parser.add_argument("--competence_id", type=str, default=DEFAULT_COMPETENCE_ID, help="ID de la compétence")
    parser.add_argument("--user_id", type=str, default=DEFAULT_USER_ID, help="ID de l'utilisateur")
    parser.add_argument("--output_dir", type=str, default="./test_data", help="Dossier de sortie")
    parser.add_argument("--count", type=int, default=10, help="Nombre de tests à générer")
    
    args = parser.parse_args()
    
    print("="*60)
    print("🧪 GÉNÉRATEUR DE JSON DE TEST")
    print("="*60)
    print(f"👤 User ID: {args.user_id}")
    print(f"🎯 Competence ID: {args.competence_id}")
    print(f"📁 Output: {args.output_dir}")
    
    # Connexion MongoDB
    try:

        MONGO_URI = "mongodb+srv://crud:H24ZJZXDzDOoVYKD@cluster0.gjtsy.mongodb.net/"
        DB_NAME = "adaptive_learning_db"
        mongo = MongoClient(MONGO_URI)

        db = mongo[DB_NAME]

        print(f"✅ Connecté à MongoDB : {DB_NAME}")
    except Exception as e:
        print(f"❌ Échec connexion MongoDB: {e}")
        return 1
    
    # Génération
    generator = TestJSONGenerator(db, args.user_id, args.competence_id)
    files = generator.generate_all(args.output_dir)
    
    if files:
        print(f"\n{'='*60}")
        print(f"✅ {len(files)} fichiers générés avec succès !")
        print(f"{'='*60}")
        print(f"\n💡 Pour tester avec curl:")
        print(f"   cd {args.output_dir}")
        print(f"   for f in test_submission_*.json; do")
        print(f"     curl -X POST http://localhost:5000/api/responses/submit \\")
        print(f"       -H 'Content-Type: application/json' \\")
        print(f"       -d @$f")
        print(f"   done")
    else:
        print("\n❌ Aucun fichier généré")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
"""
Seed Exercises - Génère N exercices pour une compétence donnée.
RESPECTE LE SCHÉMA ExerciseSchema (correct_answer, options, type, etc.)

Usage:
    python seed_exercises.py --competence_id <ID> --count <N>
    python seed_exercises.py --competence_id 69c0dcb7b7c9b6c5b218982c --count 10 --clear
"""

import sys
import os
import random
import argparse
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION MONGODB
# ═══════════════════════════════════════════════════════════════════

MONGO_URI = "mongodb+srv://crud:H24ZJZXDzDOoVYKD@cluster0.gjtsy.mongodb.net/"
DB_NAME = "adaptive_learning_db"

# Connexion
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client[DB_NAME]

# Test de connexion
try:
    client.admin.command('ping')
    print(f"✅ Connecté à MongoDB : {DB_NAME}")
except Exception as e:
    print(f"❌ Échec connexion MongoDB : {e}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# DONNÉES DE RÉFÉRENCE PAR TYPE D'EXERCICE
# ═══════════════════════════════════════════════════════════════════

EXERCISE_TYPES = {
    "qcm": {
        "templates": [
            "Quelle est la bonne définition de {concept} ?",
            "Que signifie l'acronyme {concept} ?",
            "Lequel de ces éléments correspond à {concept} ?",
        ],
        "generate_options": lambda correct: [
            correct,
            f"{correct}_wrong1",
            f"{correct}_wrong2",
            f"{correct}_wrong3"
        ][:4],
        "difficulty_range": (0.1, 0.4)
    },
    "qcm_multiple": {
        "templates": [
            "Sélectionnez toutes les bonnes réponses concernant {concept} :",
            "Lesquels de ces éléments sont vrais pour {concept} ?",
        ],
        "generate_options": lambda correct: [
            correct[0] if isinstance(correct, list) else correct,
            "Option partiellement vraie",
            "Option fausse mais plausible",
            "Option clairement fausse"
        ],
        "difficulty_range": (0.4, 0.7)
    },
    "vrai_faux": {
        "templates": [
            "{concept} est-il essentiel en Python ? (Vrai/Faux)",
            "La syntaxe de {concept} est-elle correcte ? (Vrai/Faux)",
        ],
        "generate_options": lambda correct: ["Vrai", "Faux"],
        "difficulty_range": (0.1, 0.3)
    },
    "texte_a_trous": {
        "templates": [
            "Complétez : Pour définir une fonction, on utilise le mot-clé ____.",
            "Complétez : La boucle ____ permet d'itérer sur une séquence.",
        ],
        "generate_options": lambda correct: [],  # Pas d'options pour ce type
        "difficulty_range": (0.3, 0.6)
    },
    "code_completion": {
        "templates": [
            "Complétez le code : {code_prefix}____{code_suffix}",
            "Quelle instruction manque-t-il à la ligne ____ ?",
        ],
        "generate_options": lambda correct: [],
        "difficulty_range": (0.5, 0.8)
    },
    "debugging": {
        "templates": [
            "Trouvez l'erreur dans ce code : {code_snippet}",
            "Pourquoi ce code ne fonctionne-t-il pas : {code_snippet} ?",
        ],
        "generate_options": lambda correct: [],
        "difficulty_range": (0.6, 0.9)
    }
}

# Contenu par compétence (pour générer des questions pertinentes)
COMPETENCE_CONTENT = {
    "introduction": {
        "concepts": ["Python", "langage interprété", "POO", "syntaxe simple", "bibliothèques"],
        "answers": ["Python", "interprété", "orientée objet", "simple", "standard"],
        "code_prefix": "",
        "code_suffix": "",
        "code_snippet": "print('Hello World')"
    },
    "variables": {
        "concepts": ["variable", "string", "integer", "float", "boolean", "None"],
        "answers": ["str", "int", "float", "bool", "NoneType"],
        "code_prefix": "x = ",
        "code_suffix": "",
        "code_snippet": "name = 'Alice'"
    },
    "conditions": {
        "concepts": ["if", "else", "elif", "condition", "opérateur de comparaison"],
        "answers": ["if", "else", "elif", "==", "!="],
        "code_prefix": "if ",
        "code_suffix": ":\n    pass",
        "code_snippet": "if x > 5:"
    },
    "boucles": {
        "concepts": ["for", "while", "range", "itération", "break", "continue"],
        "answers": ["for", "while", "range()", "break", "continue"],
        "code_prefix": "for i in ",
        "code_suffix": ":\n    print(i)",
        "code_snippet": "for i in range(10):"
    },
    "fonctions": {
        "concepts": ["def", "return", "paramètre", "argument", "portée", "lambda"],
        "answers": ["def", "return", "paramètre", "argument", "lambda"],
        "code_prefix": "def ",
        "code_suffix": "():\n    pass",
        "code_snippet": "def add(a, b): return a + b"
    },
    "default": {
        "concepts": ["concept", "méthode", "fonction", "variable", "objet"],
        "answers": ["correct", "valide", "true", "yes", "ok"],
        "code_prefix": "",
        "code_suffix": "",
        "code_snippet": "code_example()"
    }
}


# ═══════════════════════════════════════════════════════════════════
# GÉNÉRATEUR D'EXERCICES (RESPECTE LE SCHÉMA)
# ═══════════════════════════════════════════════════════════════════

class ExerciseGenerator:
    """Génère des exercices conformes au schéma ExerciseSchema."""
    
    VALID_TYPES = ["qcm", "qcm_multiple", "vrai_faux", "texte_a_trous", 
                   "code_completion", "code_libre", "debugging", "projet_mini"]
    VALID_STATUSES = ["planned", "generating", "generated", "error"]
    
    def __init__(self, competence_doc: dict, lesson_id: str = None):
        self.competence = competence_doc
        self.competence_id = competence_doc["_id"]
        self.competence_name = competence_doc.get("name", "Unknown").lower()
        self.level = competence_doc.get("level", 1)
        self.subject_id = competence_doc.get("subject_id")
        
        # Lesson ID : utiliser subject_id si non fourni (simplification)
        self.lesson_id = lesson_id or self.subject_id
        
        # Charger le contenu adapté
        self.content = self._load_content()
    
    def _load_content(self) -> dict:
        """Charge le contenu spécifique à la compétence."""
        name_lower = self.competence_name
        for key, value in COMPETENCE_CONTENT.items():
            if key in name_lower or key.replace("_", " ") in name_lower:
                return value
        return COMPETENCE_CONTENT["default"]
    
    def _select_exercise_type(self) -> str:
        """Sélectionne un type d'exercice adapté au niveau."""
        if self.level == 1:
            # Niveau 1 : types simples
            return random.choice(["qcm", "vrai_faux", "texte_a_trous"])
        elif self.level == 2:
            # Niveau 2 : types intermédiaires
            return random.choice(["qcm", "qcm_multiple", "code_completion"])
        else:
            # Niveau 3+ : types avancés
            return random.choice(["code_completion", "debugging", "code_libre"])
    
    def _generate_exercise_data(self, index: int) -> dict:
        """
        Génère UN exercice conforme au schéma ExerciseSchema.
        
        Champs requis :
        - competence_id, lesson_id, type, difficulty
        Champs optionnels :
        - question, options, correct_answer, explanation, hints, etc.
        """
        
        # Sélectionner le type et le template
        ex_type = self._select_exercise_type()
        type_config = EXERCISE_TYPES.get(ex_type, EXERCISE_TYPES["qcm"])
        template = random.choice(type_config["templates"])
        
        # Données de contenu
        concept = random.choice(self.content["concepts"])
        correct_answer = random.choice(self.content["answers"])
        code_prefix = self.content.get("code_prefix", "")
        code_suffix = self.content.get("code_suffix", "")
        code_snippet = self.content.get("code_snippet", "")
        
        # Générer la question
        question = template.format(
            concept=concept,
            code_prefix=code_prefix,
            code_suffix=code_suffix,
            code_snippet=code_snippet
        )
        
        # Générer les options (seulement pour QCM)
        options = []
        if ex_type in ["qcm", "qcm_multiple", "vrai_faux"]:
            options = type_config["generate_options"](correct_answer)
        
        # Difficulté adaptée au niveau et à l'index
        min_diff, max_diff = type_config["difficulty_range"]
        difficulty = round(min_diff + (index * 0.03) + random.uniform(-0.02, 0.02), 2)
        difficulty = max(0.0, min(1.0, difficulty))  # Clamp [0, 1]
        
        # Code unique
        base_code = self.competence.get("code", "EX")
        exercise_code = f"{base_code}_{index:03d}"
        
        # Hints adaptés au type
        hints = []
        if ex_type in ["qcm", "qcm_multiple"]:
            hints = [
                f"Indice : Pensez à la définition de {concept}",
                f"Indice : Éliminez les options clairement fausses",
            ]
        elif ex_type == "code_completion":
            hints = [
                f"Indice : La syntaxe commence par '{code_prefix}'",
                f"Indice : Regardez l'indentation attendue",
            ]
        
        # ✅ Construction du document EXERCISE (schéma respecté)
        return {
            # Champs requis
            "competence_id": ObjectId(self.competence_id) if isinstance(self.competence_id, str) else self.competence_id,
            "lesson_id": ObjectId(self.lesson_id) if isinstance(self.lesson_id, str) else self.lesson_id,
            "type": ex_type,  # Doit être dans VALID_TYPES
            "difficulty": difficulty,  # Float entre 0.0 et 1.0
            
            # Champs optionnels mais recommandés
            "question": question,
            "options": options,  # Liste pour QCM, vide sinon
            "correct_answer": correct_answer,  # ✅ Champ CORRECT (pas "answer")
            "explanation": f"Explication : {correct_answer} est la bonne réponse car...",
            "hints": hints,
            "code_template": f"{code_prefix}____{code_suffix}" if ex_type == "code_completion" else "",
            "expected_output": correct_answer if ex_type in ["code_completion", "debugging"] else "",
            "estimated_time": random.randint(30, 120),
            
            # Métadonnées
            "status": "generated",  # Doit être dans VALID_STATUSES
            "attempt_count": 0,  # dump_only dans le schéma, mais utile pour le seed
            "success_count": 0,
            
            # Identifiants et timestamps
            "code": exercise_code,
            "subject_id": ObjectId(self.subject_id) if isinstance(self.subject_id, str) else self.subject_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    
    def generate(self, count: int) -> list:
        """Génère N exercices."""
        exercises = []
        for i in range(1, count + 1):
            exercise = self._generate_exercise_data(i)
            exercises.append(exercise)
        return exercises


# ═══════════════════════════════════════════════════════════════════
# SEEDER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

class ExerciseSeeder:
    """Insère les exercices dans MongoDB."""
    
    def __init__(self, db):
        self.db = db
        self.collection = db["exercises"]
        self.competence_collection = db["competences"]
    
    def check_competence_exists(self, competence_id: str) -> dict:
        """Vérifie que la compétence existe."""
        competence = self.competence_collection.find_one({
            "_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        })
        
        if not competence:
            print(f"❌ Compétence {competence_id} non trouvée")
            return None
        
        print(f"✅ Compétence : {competence.get('name')} (Level {competence.get('level')})")
        return competence
    
    def clear_existing(self, competence_id: str) -> int:
        """Supprime les exercices existants pour cette compétence."""
        result = self.collection.delete_many({
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        })
        if result.deleted_count > 0:
            print(f"🗑️  {result.deleted_count} exercices supprimés")
        return result.deleted_count
    
    def insert_exercises(self, exercises: list) -> int:
        """Insère les exercices en base."""
        if not exercises:
            return 0
        
        result = self.collection.insert_many(exercises)
        return len(result.inserted_ids)
    
    def seed(self, competence_id: str, count: int, clear: bool = False, lesson_id: str = None) -> dict:
        """Exécute le seed complet."""
        
        print(f"\n{'='*70}")
        print(f"🌱 SEED EXERCISES - Schéma ExerciseSchema")
        print(f"{'='*70}")
        print(f"📅 {datetime.utcnow().isoformat()}")
        print(f"🎯 Competence ID : {competence_id}")
        print(f"📊 Count         : {count}")
        print(f"🧹 Clear         : {clear}")
        
        # Vérifier compétence
        competence = self.check_competence_exists(competence_id)
        if not competence:
            return {"success": False, "error": "Competence not found"}
        
        # Clear optionnel
        if clear:
            self.clear_existing(competence_id)
        
        # Générer
        print(f"\n🔄 Génération de {count} exercices...")
        generator = ExerciseGenerator(competence, lesson_id)
        exercises = generator.generate(count)
        
        # Valider avant insertion
        print(f"🔍 Validation des exercices...")
        for i, ex in enumerate(exercises, 1):
            assert ex["type"] in ExerciseGenerator.VALID_TYPES, f"Type invalide: {ex['type']}"
            assert 0.0 <= ex["difficulty"] <= 1.0, f"Difficulty hors range: {ex['difficulty']}"
            assert ex["status"] in ExerciseGenerator.VALID_STATUSES, f"Status invalide: {ex['status']}"
            assert "correct_answer" in ex, "Champ correct_answer manquant !"
        print(f"✅ Tous les exercices sont valides")
        
        # Insérer
        print(f"📝 Insertion en base...")
        inserted = self.insert_exercises(exercises)
        
        # Vérification
        total = self.collection.count_documents({
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        })
        
        print(f"\n{'='*70}")
        print(f"✅ SEED TERMINÉ")
        print(f"{'='*70}")
        print(f"📦 Générés  : {len(exercises)}")
        print(f"💾 Insérés  : {inserted}")
        print(f"📊 Total DB : {total}")
        
        # Afficher un exemple
        if exercises:
            ex = exercises[0]
            print(f"\n📋 EXEMPLE D'EXERCICE:")
            print(f"    Code           : {ex['code']}")
            print(f"    Type           : {ex['type']}")
            print(f"    Difficulty     : {ex['difficulty']}")
            print(f"    Question       : {ex['question'][:60]}...")
            print(f"    Correct Answer : {ex['correct_answer']}")
            print(f"    Options        : {ex['options'][:3]}{'...' if len(ex['options']) > 3 else ''}")
            print(f"    Status         : {ex['status']}")
        
        return {
            "success": True,
            "competence_id": str(competence_id),
            "competence_name": competence.get("name"),
            "generated": len(exercises),
            "inserted": inserted,
            "total": total,
        }


# ═══════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Seed exercises avec schéma valide")
    parser.add_argument("--competence_id", type=str, required=True, help="ID de la compétence")
    parser.add_argument("--count", type=int, default=10, help="Nombre d'exercices")
    parser.add_argument("--clear", action="store_true", help="Supprimer existants")
    parser.add_argument("--lesson_id", type=str, default=None, help="ID de la leçon (optionnel)")
    
    args = parser.parse_args()
    
    seeder = ExerciseSeeder(db)
    result = seeder.seed(
        competence_id=args.competence_id,
        count=args.count,
        clear=args.clear,
        lesson_id=args.lesson_id
    )
    
    if result.get("success"):
        print(f"\n🎉 Seed réussi !")
        return 0
    else:
        print(f"\n❌ Échec : {result.get('error')}")
        return 1


if __name__ == "__main__":
    exit(main())
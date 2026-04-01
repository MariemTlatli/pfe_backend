"""
Générateur de dataset synthétique pour SAINT+ (pyKT).

Deux modes :
  --small : 5 étudiants, 3 compétences, 15 interactions/étudiant (pour comprendre)
  --full  : 200 étudiants, 10 compétences, 200 interactions/étudiant (pour entraîner)

Usage :
  python scripts/generate_saint_dataset.py --small
  python scripts/generate_saint_dataset.py --full
"""

import random
import math
import csv
import os
import json
import argparse
from collections import defaultdict


# ═══════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════

SEED = 42

CONFIGS = {
    "small": {
        "n_students": 5,
        "n_skills": 3,
        "n_exercises_per_skill": 4,   # 12 exercices total
        "n_interactions": 15,          # par étudiant
        "description": "Petit dataset pédagogique"
    },
    "full": {
        "n_students": 200,
        "n_skills": 10,
        "n_exercises_per_skill": 8,   # 80 exercices total
        "n_interactions": 200,         # par étudiant
        "description": "Dataset complet pour entraînement SAINT+"
    }
}


# ═══════════════════════════════════════════════
# Fonctions utilitaires
# ═══════════════════════════════════════════════

def sigmoid(x):
    """Fonction sigmoïde bornée pour éviter overflow."""
    x = max(-10, min(10, x))
    return 1 / (1 + math.exp(-x))


def create_skills(n_skills):
    """
    Crée les compétences avec difficulté croissante.
    
    Skill 0 = plus facile (0.3)
    Skill n = plus difficile (0.8)
    """
    skills = []
    for i in range(n_skills):
        skills.append({
            "id": i,
            "name": f"competence_{i}",
            "difficulty": round(0.3 + (i / max(n_skills - 1, 1)) * 0.5, 3),
            "prerequisites": [i - 1] if i > 0 else [],
        })
    return skills


def create_exercises(skills, n_per_skill):
    """
    Crée les exercices, chaque exercice appartient à une compétence.
    La difficulté varie autour de celle de la compétence.
    """
    exercises = []
    ex_id = 0
    for skill in skills:
        for j in range(n_per_skill):
            diff = skill["difficulty"] + random.uniform(-0.15, 0.15)
            diff = round(max(0.1, min(0.95, diff)), 3)
            exercises.append({
                "id": ex_id,
                "skill_id": skill["id"],
                "difficulty": diff,
            })
            ex_id += 1
    return exercises


def create_students(n_students):
    """
    Crée les étudiants avec des profils variés.
    
    - ability : capacité innée (distribution normale centrée sur 0.5)
    - learning_rate : vitesse d'apprentissage
    - speed : vitesse de réponse (affecte le temps passé)
    """
    students = []
    for i in range(n_students):
        ability = random.gauss(0.5, 0.2)
        ability = round(max(0.1, min(0.9, ability)), 3)
        
        learning_rate = round(random.uniform(0.02, 0.08), 4)
        speed = round(random.uniform(0.5, 2.0), 2)
        
        students.append({
            "id": i,
            "ability": ability,
            "learning_rate": learning_rate,
            "speed": speed,
        })
    return students


# ═══════════════════════════════════════════════
# Simulation principale
# ═══════════════════════════════════════════════

def simulate_interactions(students, skills, exercises, n_interactions):
    """
    Simule les interactions élève-exercice.
    
    Pour chaque étudiant :
    1. Choisir une compétence (préférence pour les moins pratiquées)
    2. Choisir un exercice de cette compétence
    3. Calculer P(correct) avec le modèle
    4. Tirer le résultat (correct ou non)
    5. Calculer le temps passé
    6. Avancer le timestamp
    
    Returns:
        dict: {uid: [interactions triées par temps]}
    """
    all_data = defaultdict(list)
    
    # Index exercices par skill
    exercises_by_skill = defaultdict(list)
    for ex in exercises:
        exercises_by_skill[ex["skill_id"]].append(ex)
    
    for student in students:
        # Compteur de pratique par compétence
        skill_practice = {s["id"]: 0 for s in skills}
        
        # Temps de départ (random dans le mois de janvier 2024)
        base_timestamp = 1704067200 + random.randint(0, 2592000)  # Jan 2024
        current_ts = base_timestamp
        
        for t in range(n_interactions):
            # ── Choix de la compétence ──
            # Préférence pour les compétences moins pratiquées
            weights = []
            for s in skills:
                practice = skill_practice[s["id"]]
                w = max(1.0, 10.0 - practice * 0.5)
                weights.append(w)
            
            total_w = sum(weights)
            weights = [w / total_w for w in weights]
            chosen_skill = random.choices(skills, weights=weights, k=1)[0]
            
            # ── Choix de l'exercice ──
            chosen_exercise = random.choice(exercises_by_skill[chosen_skill["id"]])
            
            # ── Calcul P(correct) ──
            practice_count = skill_practice[chosen_skill["id"]]
            learning_effect = student["learning_rate"] * practice_count
            
            logit = (student["ability"] + learning_effect - chosen_exercise["difficulty"]) * 3
            noise = random.gauss(0, 0.3)
            p_correct = sigmoid(logit + noise)
            
            is_correct = 1 if random.random() < p_correct else 0
            
            # ── Temps de réponse (elapsed_time) ──
            base_time = 30 + chosen_exercise["difficulty"] * 60
            if is_correct == 0:
                base_time *= 1.5  # Plus de temps si faux
            elapsed = max(5, int(base_time / student["speed"] + random.gauss(0, 10)))
            
            # ── Lag time (temps entre 2 exercices) ──
            lag = random.choices(
                [random.randint(5, 30),        # Enchaînement rapide (70%)
                 random.randint(60, 600),       # Pause courte (20%)
                 random.randint(3600, 86400)],  # Longue pause (10%)
                weights=[0.7, 0.2, 0.1],
                k=1
            )[0]
            
            current_ts += elapsed + lag
            
            # ── Stocker l'interaction ──
            interaction = {
                "uid": student["id"],
                "questions": chosen_exercise["id"],
                "concepts": chosen_skill["id"],
                "responses": is_correct,
                "selectmasks": 1,
                "timestamps": current_ts,
                "elapsed_time": elapsed,
            }
            all_data[student["id"]].append(interaction)
            
            # ── Mettre à jour la pratique ──
            skill_practice[chosen_skill["id"]] += 1
    
    return all_data


# ═══════════════════════════════════════════════
# Export : CSV brut (une ligne = une interaction)
# ═══════════════════════════════════════════════

def export_raw_csv(all_data, filepath):
    """Exporte en CSV brut pour inspection / debug."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    fieldnames = ["uid", "questions", "concepts", "responses",
                  "selectmasks", "timestamps", "elapsed_time"]
    
    rows = []
    for uid in sorted(all_data.keys()):
        for interaction in all_data[uid]:
            rows.append(interaction)
    
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"  ✅ CSV brut : {filepath} ({len(rows)} lignes)")
    return len(rows)


# ═══════════════════════════════════════════════
# Export : Format pyKT (séquences multi-lignes)
# ═══════════════════════════════════════════════

def export_pykt_format(all_data, filepath):
    """
    Exporte au format séquence pyKT :
    
    n_interactions
    q1,q2,...,qn
    c1,c2,...,cn
    r1,r2,...,rn
    t1,t2,...,tn
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    n_students = 0
    with open(filepath, "w") as f:
        for uid in sorted(all_data.keys()):
            interactions = all_data[uid]
            n = len(interactions)
            
            questions = ",".join(str(x["questions"]) for x in interactions)
            concepts = ",".join(str(x["concepts"]) for x in interactions)
            responses = ",".join(str(x["responses"]) for x in interactions)
            timestamps = ",".join(str(x["timestamps"]) for x in interactions)
            
            f.write(f"{n}\n")
            f.write(f"{questions}\n")
            f.write(f"{concepts}\n")
            f.write(f"{responses}\n")
            f.write(f"{timestamps}\n")
            
            n_students += 1
    
    print(f"  ✅ pyKT format : {filepath} ({n_students} étudiants)")


# ═══════════════════════════════════════════════
# Export : Métadonnées (pour traçabilité)
# ═══════════════════════════════════════════════

def export_metadata(config, skills, exercises, students, all_data, filepath):
    """Sauvegarde les métadonnées du dataset."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Statistiques
    total_interactions = sum(len(v) for v in all_data.values())
    all_responses = []
    for uid_data in all_data.values():
        all_responses.extend([x["responses"] for x in uid_data])
    
    correct_rate = sum(all_responses) / len(all_responses) if all_responses else 0
    
    # Interactions par compétence
    skill_counts = defaultdict(int)
    skill_correct = defaultdict(int)
    for uid_data in all_data.values():
        for x in uid_data:
            skill_counts[x["concepts"]] += 1
            skill_correct[x["concepts"]] += x["responses"]
    
    metadata = {
        "config": config,
        "stats": {
            "total_students": len(all_data),
            "total_skills": len(skills),
            "total_exercises": len(exercises),
            "total_interactions": total_interactions,
            "avg_interactions_per_student": round(total_interactions / len(all_data), 1),
            "overall_correct_rate": round(correct_rate, 4),
            "correct_rate_by_skill": {
                str(sid): round(skill_correct[sid] / skill_counts[sid], 4)
                for sid in sorted(skill_counts.keys())
            },
        },
        "skills": skills,
        "exercise_count_by_skill": {
            str(s["id"]): len([e for e in exercises if e["skill_id"] == s["id"]])
            for s in skills
        },
    }
    
    with open(filepath, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  ✅ Métadonnées : {filepath}")
    return metadata


# ═══════════════════════════════════════════════
# Affichage des statistiques
# ═══════════════════════════════════════════════

def print_stats(metadata):
    """Affiche les statistiques du dataset."""
    stats = metadata["stats"]
    
    print("\n" + "=" * 60)
    print("📊 STATISTIQUES DU DATASET")
    print("=" * 60)
    print(f"  Étudiants          : {stats['total_students']}")
    print(f"  Compétences        : {stats['total_skills']}")
    print(f"  Exercices          : {stats['total_exercises']}")
    print(f"  Interactions total : {stats['total_interactions']}")
    print(f"  Moy/étudiant       : {stats['avg_interactions_per_student']}")
    print(f"  Taux de réussite   : {stats['overall_correct_rate']:.1%}")
    print()
    print("  Taux par compétence :")
    for sid, rate in stats["correct_rate_by_skill"].items():
        bar = "█" * int(rate * 30) + "░" * (30 - int(rate * 30))
        print(f"    Skill {sid:>2} : {bar} {rate:.1%}")
    print("=" * 60)


# ═══════════════════════════════════════════════
# Affichage détaillé du petit dataset
# ═══════════════════════════════════════════════

def print_small_dataset_detail(all_data, skills, exercises):
    """Affiche le détail du petit dataset pour compréhension."""
    print("\n" + "=" * 60)
    print("🔍 DÉTAIL DU PETIT DATASET")
    print("=" * 60)
    
    for uid in sorted(all_data.keys()):
        interactions = all_data[uid]
        print(f"\n── Étudiant {uid} ({len(interactions)} interactions) ──")
        print(f"  {'#':>3} {'Exercice':>8} {'Compét.':>8} {'Réponse':>8} {'Temps':>6}")
        print(f"  {'─'*3} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")
        
        for i, x in enumerate(interactions):
            status = "✅" if x["responses"] == 1 else "❌"
            print(f"  {i+1:>3} "
                  f"Ex:{x['questions']:>4} "
                  f"KC:{x['concepts']:>4} "
                  f"   {status}    "
                  f"{x['elapsed_time']:>4}s")
    
    print()


# ═══════════════════════════════════════════════
# Point d'entrée
# ═══════════════════════════════════════════════

def generate(mode="small"):
    """Génère le dataset selon le mode choisi."""
    
    random.seed(SEED)
    config = CONFIGS[mode]
    
    print(f"\n🚀 Génération : {config['description']}")
    print(f"   Mode = {mode}\n")
    
    # 1. Créer les entités
    skills = create_skills(config["n_skills"])
    exercises = create_exercises(skills, config["n_exercises_per_skill"])
    students = create_students(config["n_students"])
    
    print(f"  Compétences créées : {len(skills)}")
    print(f"  Exercices créés    : {len(exercises)}")
    print(f"  Étudiants créés    : {len(students)}")
    
    # 2. Simuler les interactions
    all_data = simulate_interactions(
        students, skills, exercises, config["n_interactions"]
    )
    
    total = sum(len(v) for v in all_data.values())
    print(f"  Interactions total : {total}")
    
    # 3. Exporter
    base_dir = f"data/{mode}"
    
    export_raw_csv(all_data, f"{base_dir}/interactions.csv")
    export_pykt_format(all_data, f"{base_dir}/pykt_format.txt")
    metadata = export_metadata(
        config, skills, exercises, students, all_data,
        f"{base_dir}/metadata.json"
    )
    
    # 4. Afficher les stats
    print_stats(metadata)
    
    # 5. Détail pour le petit dataset
    if mode == "small":
        print_small_dataset_detail(all_data, skills, exercises)
    
    return all_data, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génération dataset SAINT+")
    parser.add_argument("--mode", choices=["small", "full", "both"],
                        default="both", help="small, full, ou both")
    args = parser.parse_args()
    
    if args.mode in ("small", "both"):
        generate("small")
    
    if args.mode in ("full", "both"):
        generate("full")
    
    print("\n✅ Terminé ! Fichiers générés dans data/")
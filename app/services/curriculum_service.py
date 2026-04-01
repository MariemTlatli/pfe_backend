"""
Service Curriculum - Génération du graphe de compétences avec Ollama.
VERSION 3 ÉTAPES : Compétences → Prérequis → Graphe
"""

from app.services.ollama_service import OllamaService
from app.services.graph_service import GraphService
from app.models.competence import Competence
from app.models.subject import Subject
from app.config import Config
from app.extensions import mongo  # ← IMPORT AJOUTÉ


class CurriculumService:
    """Génération de curriculum (graphe de compétences) avec GenAI."""
    
    @staticmethod
    def generate_for_subject(subject_id):
        """
        Générer le curriculum complet pour une matière.
        APPROCHE EN 3 ÉTAPES :
        1. Générer les compétences (sans prérequis)
        2. Générer les prérequis (avec tous les codes disponibles)
        3. Construire le graphe et valider
        
        Args:
            subject_id (str): ID de la matière
            
        Returns:
            dict: {
                'competences': [...],
                'graph': {...},
                'stats': {...}
            }
        """
        # Vérifier que la matière existe
        subject = Subject.find_by_id(subject_id)
        if not subject:
            raise ValueError(f"Matière {subject_id} introuvable")
        
        # Vérifier si curriculum déjà généré
        existing = Competence.find_by_subject(subject_id)
        if existing:
            raise ValueError(f"Curriculum déjà généré pour cette matière ({len(existing)} compétences)")
        
        # ═══════════════════════════════════════════════════
        # ÉTAPE 1 : GÉNÉRER LES COMPÉTENCES (SANS PRÉREQUIS)
        # ═══════════════════════════════════════════════════
        
        print("📚 ÉTAPE 1/3 : Génération des compétences...")
        
        prompt_competences = CurriculumService._build_competences_prompt(subject)
        
        try:
            response_competences = OllamaService.generate_json(prompt_competences)
        except Exception as e:
            raise Exception(f"Erreur génération compétences: {str(e)}")
        if 'competences' not in response_competences:
            raise ValueError("Format invalide : manque 'competences'")
        
        competences_data = response_competences['competences']
        
        # Limiter le nombre
        max_comp = Config.MAX_COMPETENCES_PER_SUBJECT
        if len(competences_data) > max_comp:
            competences_data = competences_data[:max_comp]
        
        # Créer les compétences SANS prérequis
        code_to_id = {}
        
        for comp_data in competences_data:
            difficulty = comp_data.get('difficulty', 0.5)
            comp = Competence.create(
                subject_id=subject_id,
                code=comp_data['code'],
                name=comp_data['name'],
                description=comp_data.get('description', ''),
                level=comp_data.get('level', 1),
                graph_data={'x': 0, 'y': 0},
                prerequisites=[],
                difficulty_params={
                    **Competence.DEFAULT_DIFFICULTY_PARAMS,
                    "base_difficulty": difficulty
                }
            )
            code_to_id[comp_data['code']] = str(comp['_id'])
        
        print(f"✅ {len(code_to_id)} compétences créées")
        

        # print("\n🧪 MODE TEST : Fake compétences (structure réelle)")

        # # 1. Fake réponse LLM (simule le retour d'Ollama instantanément)
        # response_competences = {
        #     "competences": [
        #         {
        #             "code": "C1",
        #             "name": "Variables",
        #             "description": "Comprendre les variables",
        #             "level": 1,
        #             "difficulty": 0.2
        #         },
        #         {
        #             "code": "C2",
        #             "name": "Conditions",
        #             "description": "Structures conditionnelles",
        #             "level": 1,
        #             "difficulty": 0.3
        #         },
        #         {
        #             "code": "C3",
        #             "name": "Boucles",
        #             "description": "Boucles for et while",
        #             "level": 2,
        #             "difficulty": 0.5
        #         },
        #         {
        #             "code": "C4",
        #             "name": "Fonctions",
        #             "description": "Définir et appeler des fonctions",
        #             "level": 2,
        #             "difficulty": 0.6
        #         }
        #     ]
        # }

        # competences_data = response_competences['competences']

        # # 2. Création RÉELLE en base (rapide, pas de LLM)
        # # Cela génère des ObjectIds valides et insère les documents
        # code_to_id = {}
        
        # for comp_data in competences_data:
        #     difficulty = comp_data.get('difficulty', 0.5)
            
        #     # Utilise Competence.create pour avoir un vrai ID et une vraie insertion
        #     comp = Competence.create(
        #         subject_id=subject_id,
        #         code=comp_data['code'],
        #         name=comp_data['name'],
        #         description=comp_data.get('description', ''),
        #         level=comp_data.get('level', 1),
        #         graph_data={'x': 0, 'y': 0},
        #         prerequisites=[],
        #         difficulty_params={
        #             **Competence.DEFAULT_DIFFICULTY_PARAMS,
        #             "base_difficulty": difficulty
        #         }
        #     )
        #     # Récupère le vrai ObjectId généré
        #     code_to_id[comp_data['code']] = str(comp['_id'])

        # print(f"✅ {len(code_to_id)} compétences créées (REAL DB avec Fake Data)")
        # print("📌 code_to_id:", code_to_id)

        
        # ═══════════════════════════════════════════════════
        # ÉTAPE 2 : GÉNÉRER LES PRÉREQUIS (DEBUG VERSION)
        # ═══════════════════════════════════════════════════

        print("\n🔗 ÉTAPE 2/3 : Génération des prérequis...")

        # Préparer les données
        all_codes = list(code_to_id.keys())

        print("📌 ALL CODES:", all_codes)
        print("📌 NB COMPETENCES:", len(competences_data))

        # Construire le prompt
        prompt_prerequisites = CurriculumService._build_prerequisites_prompt(
            subject, 
            competences_data,
            all_codes
        )

        print("\n📤 PROMPT PREREQUIS:\n", prompt_prerequisites)

        # Appel LLM
        try:
            response_prerequisites = OllamaService.generate_json(prompt_prerequisites)
        except Exception as e:
            print("❌ ERREUR LLM:", str(e))
            
            # rollback
            for comp_id in code_to_id.values():
                Competence.delete(comp_id)
                
            raise Exception(f"Erreur génération prérequis: {str(e)}")

        print("\n📥 RAW RESPONSE PREREQUIS:")
        print(response_prerequisites)
        print("📥 TYPE:", type(response_prerequisites))

        # Vérifier structure globale
        if not isinstance(response_prerequisites, dict):
            raise ValueError("❌ La réponse LLM n'est pas un dictionnaire")

        print("📥 KEYS:", response_prerequisites.keys())

        # Tolérance aux variantes de clés
        if 'prerequisites' in response_prerequisites:
            prerequisites_data = response_prerequisites['prerequisites']
        elif 'links' in response_prerequisites:
            print("⚠️ 'links' détecté → conversion automatique")
            prerequisites_data = response_prerequisites['links']
        elif 'edges' in response_prerequisites:
            print("⚠️ 'edges' détecté → conversion automatique")
            prerequisites_data = response_prerequisites['edges']
        else:
            # rollback
            for comp_id in code_to_id.values():
                Competence.delete(comp_id)
                
            raise ValueError(f"❌ Format invalide. Clés reçues: {list(response_prerequisites.keys())}")

        # Vérifier type liste
        if not isinstance(prerequisites_data, list):
            raise ValueError("❌ 'prerequisites' doit être une liste")

        print(f"📊 {len(prerequisites_data)} prérequis reçus")

        # Traitement des prérequis
        added_count = 0
        skipped_count = 0

        for i, prereq_data in enumerate(prerequisites_data):
            print(f"\n🔍 PREREQ #{i} RAW:", prereq_data)
            
            if not isinstance(prereq_data, dict):
                print("❌ Ignoré (pas un dict)")
                skipped_count += 1
                continue

            # Tolérance aux différents formats
            comp_code = (
                prereq_data.get('competence') or
                prereq_data.get('source') or
                prereq_data.get('from')
            )
            
            req_code = (
                prereq_data.get('requires') or
                prereq_data.get('target') or
                prereq_data.get('to')
            )
            
            strength = prereq_data.get('strength', 1.0)

            print(f"➡️ competence: {comp_code}")
            print(f"➡️ requires: {req_code}")

            # Vérification existence
            if comp_code not in code_to_id:
                print(f"❌ competence inconnue: {comp_code}")
                skipped_count += 1
                continue
                
            if req_code not in code_to_id:
                print(f"❌ requires inconnu: {req_code}")
                skipped_count += 1
                continue

            # Éviter auto-dépendance
            if comp_code == req_code:
                print("⚠️ Auto-dépendance ignorée")
                skipped_count += 1
                continue

            # Ajouter en DB
            try:
                Competence.add_prerequisite(
                    code_to_id[comp_code],
                    code_to_id[req_code],
                    strength
                )
                added_count += 1
                print("✅ Ajouté")
                
            except Exception as e:
                print(f"❌ Erreur DB: {str(e)}")
                skipped_count += 1

        print("\n📊 RÉSULTAT ÉTAPE 2:")
        print(f"✅ Ajoutés: {added_count}")
        print(f"⚠️ Ignorés: {skipped_count}")

        if added_count == 0:
            print("🚨 WARNING: Aucun prérequis ajouté ! Problème probable du LLM")

        print("✅ Étape 2 terminée")
                
        # ═══════════════════════════════════════════════════
        # ÉTAPE 3 : CONSTRUIRE LE GRAPHE ET VALIDER
        # ═══════════════════════════════════════════════════
        
        print("🕸️  ÉTAPE 3/3 : Construction du graphe...")
        
        # Récupérer les compétences avec leurs prérequis
        competences = Competence.find_by_subject(subject_id)
        
        # Valider le graphe (DAG)
        is_valid, message = GraphService.validate_dag(competences)
        if not is_valid:
            print(f"❌ Graphe invalide : {message}")
            print("🔄 Tentative de réparation automatique...")
            
            # Essayer de réparer en supprimant les cycles
            success = CurriculumService._try_fix_graph(competences)
            
            if not success:
                # Si échec, supprimer tout
                for comp in competences:
                    Competence.delete(comp['_id'])
                raise ValueError(f"Graphe invalide et non réparable: {message}")
        
        print("✅ Graphe valide (DAG)")
        
        # Calculer les niveaux (profondeur)
        levels = GraphService.calculate_levels(competences)
        for comp_id, level in levels.items():
            Competence.update_level(comp_id, level)
        
        # Calculer les positions
        positions = GraphService.calculate_layout(competences)
        for comp in competences:
            comp_id_str = str(comp['_id'])
            if comp_id_str in positions:
                Competence.update_graph_data(comp['_id'], positions[comp_id_str])
        
        # Récupérer les compétences finales
        competences_final = Competence.find_by_subject(subject_id)
        
        print("✅ Curriculum généré avec succès !")
        
        # Construire la réponse
        return {
            'subject': Subject.to_dict(subject),
            'has_curriculum': True,
            'competences': [
                Competence.to_dict(c, include_prerequisites=True) 
                for c in competences_final
            ],
            'graph': GraphService.build_graph_data(competences_final),
            'stats': {
                'total_competences': len(competences_final),
                'total_prerequisites': sum(len(c.get('prerequisites', [])) for c in competences_final),
                'average_prerequisites_per_competence': (sum(len(c.get('prerequisites', [])) for c in competences_final) / len(competences_final)) if competences_final else 0,
                'max_depth': max(levels.values()) if levels else 0
            },
            'message': "Curriculum généré avec succès"
        }
    
    @staticmethod
    def _build_competences_prompt(subject):
        """
        Prompt ÉTAPE 1 : Générer les compétences (sans prérequis).
        """
        max_comp = Config.MAX_COMPETENCES_PER_SUBJECT
        
        prompt = f"""Tu es un expert pédagogique. Crée une liste de compétences essentielles pour la matière suivante.

**MATIÈRE** : {subject['name']}
**DESCRIPTION** : {subject.get('description', 'Non spécifiée')}

**MISSION** : Génère entre 12 et {max_comp} compétences SANS les prérequis (on les ajoutera après).

**FORMAT DE RÉPONSE (JSON STRICT)** :

{{
  "competences": [
    {{
      "code": "BAS001",
      "name": "Syntaxe de base",
      "description": "Comprendre la structure générale d'un programme, l'indentation, les commentaires.",
      "level": 1,
      "difficulty": 0.10
    }},
    {{
      "code": "VAR001",
      "name": "Variables et types",
      "description": "Déclarer des variables, comprendre les types primitifs (int, float, string, boolean).",
      "level": 1,
      "difficulty": 0.15
    }},
    {{
      "code": "COND001",
      "name": "Conditions",
      "description": "Utiliser if, else, elif pour créer des branchements logiques.",
      "level": 2,
      "difficulty": 0.30
    }},
    {{
      "code": "LOOP001",
      "name": "Boucles",
      "description": "Maîtriser for et while pour répéter des instructions.",
      "level": 2,
      "difficulty": 0.35
    }},
    {{
      "code": "FUNC001",
      "name": "Fonctions",
      "description": "Créer des fonctions avec def, utiliser paramètres et return.",
      "level": 3,
      "difficulty": 0.45
    }}
  ]
}}

**CONSIGNES** :

1. **CODE** : Format XXX001 (3 lettres MAJUSCULES + 3 chiffres)
   - Tous les codes doivent être UNIQUES
   - Exemples : BAS001, VAR001, COND001, LOOP001, FUNC001, etc.

2. **NAME** : Titre court et clair (max 50 caractères)

3. **DESCRIPTION** : Explication pédagogique précise (2-3 phrases)
   - Qu'est-ce que l'apprenant va maîtriser ?
   - Quels sont les concepts clés ?

4. **LEVEL** : Niveau suggéré
   - 1 = Fondamentaux (concepts de base)
   - 2 = Intermédiaire (combine plusieurs concepts)
   - 3 = Avancé (notions complexes)
   - 4 = Expert (maîtrise approfondie)

5. **DIFFICULTY** : Entre 0.0 et 1.0
   - 0.0-0.2 : Très facile
   - 0.2-0.4 : Facile
   - 0.4-0.6 : Moyen
   - 0.6-0.8 : Difficile
   - 0.8-1.0 : Très difficile

6. **ORGANISATION** :
   - Commence par les fondamentaux (level 1)
   - Progresse vers les concepts avancés (level 2, 3, 4)
   - Couvre tous les aspects importants de la matière

**NE GÉNÈRE PAS** les prérequis maintenant, on le fera dans une deuxième étape.

**IMPORTANT** : Réponds UNIQUEMENT avec le JSON, sans texte avant/après, sans markdown, sans ```json.
"""
        return prompt
    
    @staticmethod
    def _build_prerequisites_prompt(subject, competences_data, all_codes):
        """
        Prompt ÉTAPE 2 : Générer les prérequis.
        """
        # Construire la liste des compétences pour le contexte
        comp_list = "\n".join([
            f"  - {c['code']} : {c['name']} (level {c['level']}, difficulté {c.get('difficulty', 0.5):.2f})"
            for c in competences_data
        ])
        
        codes_str = ", ".join(all_codes)
        
        prompt = f"""Tu es un expert pédagogique. Tu dois définir les PRÉREQUIS entre les compétences suivantes pour la matière **{subject['name']}**.

**COMPÉTENCES DISPONIBLES** :

{comp_list}

**CODES DISPONIBLES** : {codes_str}
⚠️ TRÈS IMPORTANT :
UTILISE STRICTEMENT ces codes : {', '.join(all_codes)}
NE JAMAIS inventer d'autres codes (VAR001, BAS001, etc.)
**MISSION** : Crée les liens de prérequis pour former un graphe d'apprentissage progressif.

**FORMAT DE RÉPONSE (JSON STRICT)** :

{{
  "prerequisites": [
    {{
      "competence": "C1",
      "requires": "C2",
      "strength": 1.0
    }}
  ]
}}

**CONSIGNES STRICTES** :

1. **STRUCTURE** :
   - `competence` : code de la compétence qui a besoin du prérequis
   - `requires` : code de la compétence prérequise
   - `strength` : importance du prérequis (0.5 à 1.0)
     * 1.0 = absolument indispensable
     * 0.8 = fortement recommandé
     * 0.7 = recommandé
     * 0.5 = utile mais pas critique

2. **RÈGLES PÉDAGOGIQUES** :
   - Une compétence peut avoir 0 à 3 prérequis
   - Les fondamentaux (level 1) ont généralement 0 ou 1 prérequis
   - Les compétences avancées (level 3+) ont 2-3 prérequis
   - Les prérequis doivent être logiques :
     * On ne peut pas utiliser les boucles sans connaître les variables
     * On ne peut pas faire de la récursivité sans connaître les fonctions
     * etc.

3. **GRAPHE VALIDE (TRÈS IMPORTANT)** :
   - PAS DE CYCLE : A ne peut pas dépendre de B si B dépend de A
   - PAS DE CYCLE INDIRECT : A → B → C → A est INTERDIT
   - TOUS les codes doivent exister dans : {codes_str}
   - Au moins 2-3 compétences RACINES (sans prérequis)

4. **PROGRESSION** :
   - Crée des CHEMINS D'APPRENTISSAGE clairs
   - Des fondamentaux vers les concepts avancés
   - Chaque compétence doit être accessible après avoir maîtrisé ses prérequis

**VÉRIFICATIONS AVANT DE RÉPONDRE** :
✓ Tous les codes existent dans la liste : {codes_str}
✓ Aucun cycle dans le graphe
✓ Au moins 2-3 compétences racines (sans prérequis)
✓ Les prérequis sont logiques et pédagogiques

# ⚠️ RÈGLES CRITIQUES DU GRAPHE (À SUIVRE IMPÉRATIVEMENT)

1.  **HIÉRARCHIE DES NIVEAUX (RÈGLE D'OR)** : Une compétence ne peut avoir comme prérequis qu'une compétence de **niveau inférieur ou égal**. C'est le meilleur moyen d'éviter les cycles.
    - **AUTORISÉ** : Une compétence `level: 3` peut dépendre d'une compétence `level: 2`.
    - **INTERDIT** : Une compétence `level: 2` ne peut **JAMAIS** dépendre d'une compétence `level: 3`.

2.  **PAS DE CYCLES** : Une compétence `A` ne peut pas dépendre d'une `B` si `B` dépend déjà (directement ou indirectement) de `A`. La règle de hiérarchie ci-dessus t'aidera à respecter cela.
    - *Exemple d'interdiction* : Si tu crées `{{ "competence": "C3", "requires": "C2" }}`, alors tu ne pourras **JAMAIS** créer `{{ "competence": "C2", "requires": "C3" }}`.

    Le graphe DOIT former **UNE SEULE composante connexe**.

- Au moins **2-3 compétences racines** (level 1, sans prérequis)
- TOUTES les autres compétences doivent être **accessibles** depuis au moins une racine
- Il ne doit PAS exister de "compétences isolées" sans lien avec le reste

**Stratégie pour garantir la connexité** :
1. Identifie 2-3 compétences fondamentales (level 1) comme **racines**
2. Chaque compétence de level 2 doit dépendre d'AU MOINS une racine
3. Chaque compétence de level 3+ doit dépendre d'AU MOINS une compétence de level 2
4. Assure-toi qu'il n'y a pas de "groupe isolé" de compétences

**Exemple CORRECT** :
- Racines : C1, C2
- Level 2 : C3 dépend de C1, C4 dépend de C2
- Level 3 : C5 dépend de C3 et C4

**Exemple INCORRECT** (fragmenté) :
- Groupe 1 : C1 → C2 → C3
- Groupe 2 (isolé !) : C4 → C5  ← PAS DE LIEN avec Groupe 1
    
**IMPORTANT** : Réponds UNIQUEMENT avec le JSON, sans texte avant/après, sans markdown, sans ```json.
"""
        return prompt
    
    @staticmethod
    def _try_fix_graph(competences):
        """
        Tenter de réparer automatiquement un graphe avec cycle.
        
        Stratégie : Supprimer les arêtes qui créent des cycles.
        
        Returns:
            bool: True si réparé avec succès
        """
        import networkx as nx
        
        G = GraphService.build_networkx_graph(competences)
        
        # Tant qu'il y a des cycles
        max_iterations = 10
        iteration = 0
        
        while not nx.is_directed_acyclic_graph(G) and iteration < max_iterations:
            try:
                # Trouver un cycle
                cycle = nx.find_cycle(G)
                
                # Supprimer l'arête la plus faible du cycle
                min_strength = float('inf')
                edge_to_remove = None
                
                for u, v in cycle:
                    edge_data = G.get_edge_data(u, v)
                    strength = edge_data.get('strength', 1.0) if edge_data else 1.0
                    
                    if strength < min_strength:
                        min_strength = strength
                        edge_to_remove = (u, v)
                
                if edge_to_remove:
                    # Supprimer dans le graphe NetworkX
                    G.remove_edge(*edge_to_remove)
                    
                    # Supprimer dans MongoDB
                    u_id, v_id = edge_to_remove
                    Competence.remove_prerequisite(v_id, u_id)
                    
                    print(f"🔧 Suppression du lien {u_id} → {v_id} (strength={min_strength:.2f})")
                
                iteration += 1
                
            except nx.NetworkXNoCycle:
                # Plus de cycle !
                break
        
        # Vérifier si réparé
        competences_refreshed = Competence.find_by_subject(competences[0]['subject_id'])
        is_valid, _ = GraphService.validate_dag(competences_refreshed)
        
        return is_valid
    
    @staticmethod
    def regenerate_for_subject(subject_id):
        """
        Régénérer le curriculum (supprime l'ancien).
        
        Args:
            subject_id (str): ID de la matière
            
        Returns:
            dict: Nouveau curriculum généré
        """
        # Supprimer l'ancien curriculum
        existing = Competence.find_by_subject(subject_id)
        for comp in existing:
            Competence.delete(comp['_id'])
        
        # Générer le nouveau
        return CurriculumService.generate_for_subject(subject_id)
    
    @staticmethod
    def regenerate_prerequisites_only(subject_id):
        """
        Régénérer SEULEMENT les prérequis (garde les compétences).
        Utile si le graphe généré n'est pas satisfaisant.
        
        Args:
            subject_id (str): ID de la matière
            
        Returns:
            dict: Curriculum avec nouveaux prérequis
        """
        subject = Subject.find_by_id(subject_id)
        if not subject:
            raise ValueError(f"Matière {subject_id} introuvable")
        
        competences = Competence.find_by_subject(subject_id)
        if not competences:
            raise ValueError("Aucune compétence à régénérer")
        
        # Supprimer tous les prérequis existants
        for comp in competences:
            mongo.db[Competence.COLLECTION].update_one(
                {'_id': comp['_id']},
                {'$set': {'prerequisites': []}}
            )
        
        # Préparer les données pour le prompt
        competences_data = [
            {
                'code': c['code'],
                'name': c['name'],
                'description': c.get('description', ''),
                'level': c.get('level', 1),
                'difficulty': c.get('difficulty', 0.5)
            }
            for c in competences
        ]
        
        all_codes = [c['code'] for c in competences]
        code_to_id = {c['code']: str(c['_id']) for c in competences}
        
        # Générer les nouveaux prérequis
        prompt = CurriculumService._build_prerequisites_prompt(
            subject,
            competences_data,
            all_codes
        )
        
        response = OllamaService.generate_json(prompt)
        
        if 'prerequisites' not in response:
            raise ValueError("Format invalide : manque 'prerequisites'")
        
        # Ajouter les prérequis
        for prereq_data in response['prerequisites']:
            comp_code = prereq_data.get('competence')
            req_code = prereq_data.get('requires')
            strength = prereq_data.get('strength', 1.0)
            
            if comp_code in code_to_id and req_code in code_to_id:
                Competence.add_prerequisite(
                    code_to_id[comp_code],
                    code_to_id[req_code],
                    strength
                )
        
        # Valider et retourner
        competences_updated = Competence.find_by_subject(subject_id)
        is_valid, message = GraphService.validate_dag(competences_updated)
        
        if not is_valid:
            raise ValueError(f"Graphe invalide: {message}")
        
        # Recalculer niveaux et positions
        levels = GraphService.calculate_levels(competences_updated)
        for comp_id, level in levels.items():
            Competence.update_level(comp_id, level)
        
        positions = GraphService.calculate_layout(competences_updated)
        for comp in competences_updated:
            comp_id_str = str(comp['_id'])
            if comp_id_str in positions:
                Competence.update_graph_data(comp['_id'], positions[comp_id_str])
        
        competences_final = Competence.find_by_subject(subject_id)
        
        return {
            'competences': [Competence.to_dict(c, include_prerequisites=True) for c in competences_final],
            'graph': GraphService.build_graph_data(competences_final),
            'stats': GraphService.get_graph_stats(competences_final)
        }
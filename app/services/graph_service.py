"""
Service Graph - Validation et manipulation de graphes avec NetworkX.
"""

import networkx as nx


class GraphService:
    """Gestion et validation des graphes de compétences (DAG)."""
    
    @staticmethod
    def build_networkx_graph(competences):
        """
        Construire un graphe NetworkX à partir des compétences.
        
        Args:
            competences (list): Liste de documents de compétences
            
        Returns:
            nx.DiGraph: Graphe orienté
        """
        G = nx.DiGraph()
        
        # Ajouter les nœuds
        for comp in competences:
            G.add_node(
                str(comp['_id']),
                code=comp['code'],
                name=comp['name'],
                level=comp.get('level', 1)
            )
        
        # Ajouter les arêtes (prérequis)
        for comp in competences:
            for prereq in comp.get('prerequisites', []):
                # Arête de prérequis vers compétence
                G.add_edge(
                    str(prereq['competence_id']),
                    str(comp['_id']),
                    strength=prereq.get('strength', 1.0)
                )
        
        return G
    
    @staticmethod
    def validate_dag(competences):
        """
        Valider que le graphe est un DAG (Directed Acyclic Graph).
        
        Args:
            competences (list): Liste de compétences
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not competences:
            return True, "Graphe vide (valide)"
        
        G = GraphService.build_networkx_graph(competences)
        
        # Vérifier s'il y a des cycles
        if not nx.is_directed_acyclic_graph(G):
            try:
                cycle = nx.find_cycle(G)
                codes = [G.nodes[node]['code'] for node, _ in cycle]
                return False, f"Cycle détecté: {' -> '.join(codes)}"
            except:
                return False, "Cycle détecté dans le graphe"
        
        # Vérifier la connectivité faible (tous les nœuds sont atteignables)
        if not nx.is_weakly_connected(G):
            components = list(nx.weakly_connected_components(G))
            return False, f"Graphe fragmenté en {len(components)} composantes"
        
        return True, "Graphe valide (DAG)"
    
    @staticmethod
    def calculate_levels(competences):
        """
        Calculer le niveau (profondeur) de chaque compétence dans le graphe.
        
        Args:
            competences (list): Liste de compétences
            
        Returns:
            dict: {competence_id: level}
        """
        G = GraphService.build_networkx_graph(competences)
        
        # Trouver les nœuds sans prédécesseurs (racines)
        roots = [n for n in G.nodes() if G.in_degree(n) == 0]
        
        levels = {}
        
        # Parcours en largeur pour calculer les niveaux
        for root in roots:
            for node in nx.descendants(G, root) | {root}:
                # Niveau = longueur du plus long chemin depuis une racine
                paths = []
                for r in roots:
                    if nx.has_path(G, r, node):
                        try:
                            path_length = nx.shortest_path_length(G, r, node)
                            paths.append(path_length)
                        except:
                            pass
                
                levels[node] = max(paths) + 1 if paths else 1
        
        return levels
    
    @staticmethod
    def calculate_layout(competences, algorithm='hierarchical'):
        """
        Calculer les positions (x, y) des compétences pour visualisation.
        
        Args:
            competences (list): Liste de compétences
            algorithm (str): 'hierarchical', 'spring', 'circular'
            
        Returns:
            dict: {competence_id: {x: float, y: float}}
        """
        G = GraphService.build_networkx_graph(competences)
        
        if algorithm == 'hierarchical':
            # Layout hiérarchique (par niveaux)
            pos = nx.spring_layout(G, k=2, iterations=50)
            levels = GraphService.calculate_levels(competences)
            
            # Ajuster les positions selon les niveaux
            for node in pos:
                level = levels.get(node, 1)
                pos[node] = (pos[node][0] * 500, level * 150)
        
        elif algorithm == 'spring':
            pos = nx.spring_layout(G, k=1, iterations=50, scale=500)
        
        elif algorithm == 'circular':
            pos = nx.circular_layout(G, scale=500)
        
        else:
            pos = nx.random_layout(G, scale=500)
        
        # Convertir en format dict
        positions = {}
        for node, (x, y) in pos.items():
            positions[node] = {'x': float(x), 'y': float(y)}
        
        return positions
    
    @staticmethod
    def get_root_nodes(competences):
        """
        Retourne les nœuds racines (sans prérequis).

        Args:
            competences (list): Liste des compétences

        Returns:
            list: IDs des compétences qui n'ont aucun prérequis
        """
        # Un nœud racine n'a aucun prédécesseur
        roots = []
        for comp in competences:
            prereqs = comp.get('prerequisites', [])
            if not prereqs:
                roots.append(str(comp['_id']))
        return roots
    
    @staticmethod
    def get_leaf_nodes(competences):
        """
        Retourne les nœuds feuilles (compétences terminales).
    
        Args:
            competences (list): Liste des compétences
        
        Returns:
            list: IDs des compétences qui ne sont prérequis d'aucune autre
        """
        # Construire l'ensemble de tous les prérequis
        all_prerequisites = set()
        for comp in competences:
            for prereq in comp.get('prerequisites', []):
                all_prerequisites.add(str(prereq['competence_id']))
    
        # Les feuilles sont les compétences qui ne sont dans aucun prérequis
        leaf_nodes = []
        for comp in competences:
            comp_id = str(comp['_id'])
            if comp_id not in all_prerequisites:
                leaf_nodes.append(comp_id)
    
        return leaf_nodes
    
    @staticmethod
    def get_longest_path(competences):
        """
        Calcule la longueur du plus long chemin dans le graphe.

        Args:
            competences (list): Liste des compétences

        Returns:
            list: Liste d'IDs correspondant au chemin le plus long
        """
        G = GraphService.build_networkx_graph(competences)
        try:
            path = nx.dag_longest_path(G)
            return path
        except Exception:
            return []
    
    @staticmethod
    def get_learning_path(competences, start_competence_id=None):
        """
        Obtenir un parcours d'apprentissage optimal (tri topologique).
        
        Args:
            competences (list): Liste de compétences
            start_competence_id (str, optional): Commencer par une compétence spécifique
            
        Returns:
            list: Liste ordonnée de competence_id
        """
        G = GraphService.build_networkx_graph(competences)
        
        try:
            # Tri topologique (ordre d'apprentissage)
            path = list(nx.topological_sort(G))
            
            if start_competence_id:
                # Filtrer pour ne garder que les descendants
                descendants = nx.descendants(G, start_competence_id) | {start_competence_id}
                path = [n for n in path if n in descendants]
            
            return path
        
        except nx.NetworkXError:
            # Graphe cyclique
            return []
    
    @staticmethod
    def get_prerequisites_chain(competences, competence_id):
        """
        Obtenir la chaîne complète des prérequis pour une compétence.
        
        Args:
            competences (list): Liste de compétences
            competence_id (str): ID de la compétence
            
        Returns:
            list: Liste des IDs des prérequis (ordre topologique)
        """
        G = GraphService.build_networkx_graph(competences)
        
        # Tous les prédécesseurs (prérequis directs et indirects)
        predecessors = nx.ancestors(G, competence_id)
        
        # Sous-graphe des prérequis
        subgraph = G.subgraph(predecessors | {competence_id})
        
        # Tri topologique
        try:
            return list(nx.topological_sort(subgraph))
        except:
            return list(predecessors)
    
    @staticmethod
    def build_graph_data(competences):
        """
        Construire les données du graphe pour le frontend (format compatible React Flow, D3, etc.).
        
        Args:
            competences (list): Liste de compétences
            
        Returns:
            dict: {nodes: [...], edges: [...]}
        """
        nodes = []
        edges = []
        
        for comp in competences:
            nodes.append({
                'id': str(comp['_id']),
                'code': comp['code'],
                'name': comp['name'],
                'level': comp.get('level', 1),
                'position': comp.get('graph_data', {'x': 0, 'y': 0})
            })
            
            for prereq in comp.get('prerequisites', []):
                edges.append({
                    'id': f"{prereq['competence_id']}-{comp['_id']}",
                    'source': str(prereq['competence_id']),
                    'target': str(comp['_id']),
                    'strength': prereq.get('strength', 1.0)
                })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    @staticmethod
    def visualize_graph(competences, subject_name="Curriculum", subject_id=None):
        """
        Générer une image PNG du graphe de compétences.
        
        Args:
            competences (list): Liste des compétences
            subject_name (str): Nom de la matière
            subject_id (str): ID de la matière (pour le nom du fichier)
            
        Returns:
            str: Chemin du fichier PNG généré
        """
        import matplotlib
        matplotlib.use('Agg')  # Backend non-interactif
        import matplotlib.pyplot as plt
        from pathlib import Path
        import os
        
        if not competences:
            raise ValueError("Aucune compétence à visualiser")
        
        # ═══════════════════════════════════════════════════
        # CRÉER LE DOSSIER (avec gestion d'erreurs)
        # ═══════════════════════════════════════════════════
        
        # Chemin absolu depuis la racine du projet
        base_dir = Path(__file__).resolve().parent.parent  # Remonte à app/
        output_dir = base_dir / "static" / "graphs"
        
        # Créer le dossier ET ses parents si nécessaire
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Dossier créé/vérifié : {output_dir}")
        except Exception as e:
            print(f"❌ Erreur création dossier : {e}")
            # Fallback : utiliser un dossier temporaire
            import tempfile
            output_dir = Path(tempfile.gettempdir()) / "adaptive_learning_graphs"
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"⚠️ Utilisation dossier temporaire : {output_dir}")
        
        # Construire le graphe NetworkX
        G = GraphService.build_networkx_graph(competences)
        
        # Créer un mapping id -> compétence pour accès rapide
        comp_map = {str(c['_id']): c for c in competences}
        
        # ── Calculer la profondeur de chaque nœud ──
        profondeurs = {}
        for noeud in nx.topological_sort(G):
            prereqs = list(G.predecessors(noeud))
            if not prereqs:
                profondeurs[noeud] = 0
            else:
                profondeurs[noeud] = max(profondeurs[p] for p in prereqs) + 1
        
        # ── Regrouper par profondeur (couches) ──
        couches = {}
        for noeud, prof in profondeurs.items():
            if prof not in couches:
                couches[prof] = []
            couches[prof].append(noeud)
        
        # ── Calculer les positions ──
        pos = {}
        x_spacing = 2.5
        y_spacing = 1.5
        
        for prof, noeuds in couches.items():
            num_noeuds = len(noeuds)
            for i, noeud in enumerate(sorted(noeuds)):
                x = prof * x_spacing
                y = (i - (num_noeuds - 1) / 2) * y_spacing
                pos[noeud] = (x, y)
        
        # ── Couleurs des nœuds selon le niveau ──
        couleurs = []
        labels = {}
        
        for noeud in G.nodes():
            comp = comp_map.get(noeud)
            if comp:
                # Limiter la longueur du nom pour l'affichage
                name = comp['name']
                if len(name) > 20:
                    name = name[:17] + "..."
                labels[noeud] = f"{comp['code']}\n{name}"
                level = comp.get('level', 1)
                
                # Couleur selon le niveau
                if level == 0 or level == 1:
                    couleurs.append("#BBDEFB")  # Bleu clair (fondamentaux)
                elif level == 2:
                    couleurs.append("#C8E6C9")  # Vert clair (intermédiaire)
                elif level == 3:
                    couleurs.append("#FFF9C4")  # Jaune (avancé)
                else:
                    couleurs.append("#FFE0B2")  # Orange (expert)
            else:
                labels[noeud] = noeud
                couleurs.append("#E0E0E0")
        
        # ── Créer la figure ──
        fig, ax = plt.subplots(figsize=(16, 10))
        
        # ── Dessiner le graphe ──
        nx.draw(
            G,
            pos,
            labels=labels,
            node_color=couleurs,
            node_size=3500,
            font_size=8,
            font_weight="bold",
            edge_color="#757575",
            arrows=True,
            arrowsize=20,
            arrowstyle="->",
            connectionstyle="arc3,rad=0.1",
            ax=ax,
            node_shape="s",  # Carré
            linewidths=2,
            edgecolors="#424242"
        )
        
        # ── Titre et légende ──
        ax.set_title(
            f"Graphe de Prérequis — {subject_name}\n"
            f"🔵 Fondamentaux  🟢 Intermédiaire  🟡 Avancé  🟠 Expert",
            fontsize=14,
            fontweight="bold",
            pad=20
        )
        
        plt.tight_layout()
        
        # ── Sauvegarder ──
        filename = f"curriculum_{subject_id or 'graph'}.png"
        file_path = output_dir / filename
        
        try:
            plt.savefig(file_path, dpi=150, bbox_inches="tight", facecolor='white')
            print(f"✅ Image sauvegardée : {file_path}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde : {e}")
            raise
        finally:
            plt.close()
        
        return str(file_path)

    @staticmethod
    def get_graph_stats(competences):
        """
        Obtenir les statistiques du graphe.
        
        Args:
            competences (list): Liste de documents de compétences
        
        Returns:
            dict: Statistiques complètes
        """
        if not competences:
            return {
                'total_competences': 0,
                'total_edges': 0,
                'max_level': 0,
                'root_nodes': 0,
                'leaf_nodes': 0,
                'longest_path': 0,
                'is_valid_dag': True
            }
        
        levels = GraphService.calculate_levels(competences)
        
        return {
            'total_competences': len(competences),
            'total_edges': sum(len(c.get('prerequisites', [])) for c in competences),
            'max_level': max(levels.values()) if levels else 0,
            'root_nodes': len(GraphService.get_root_nodes(competences)),
            'leaf_nodes': len(GraphService.get_leaf_nodes(competences)),
            'longest_path': len(GraphService.get_longest_path(competences)),
            'is_valid_dag': GraphService.validate_dag(competences)[0]
        }
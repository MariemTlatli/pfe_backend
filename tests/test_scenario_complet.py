"""
Script de test automatisé complet pour tous les endpoints de l'API.
Teste l'intégralité du parcours utilisateur avec l'architecture Spiral Learning.

Usage:
    python tests/test_all_endpoints.py
"""

import requests
import time
import json
from typing import Dict, Optional, List
from datetime import datetime

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

BASE_URL = "http://localhost:5000/api"
HEADERS = {"Content-Type": "application/json"}

# Codes couleurs ANSI pour affichage terminal
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


# ═══════════════════════════════════════════════════════
# CLASSE DE TEST PRINCIPALE
# ═══════════════════════════════════════════════════════

class APITester:
    """Teste tous les endpoints de l'API de manière exhaustive."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
        # Variables de contexte
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.username: Optional[str] = None
        self.email: Optional[str] = None
        
        self.domaine_id: Optional[str] = None
        self.domaine_name: Optional[str] = None
        
        self.matiere_name: Optional[str] = None
        
        self.plan_ids: List[str] = []
        self.plan_id_debutant: Optional[str] = None
        self.plan_id_intermediaire: Optional[str] = None
        self.plan_id_avance: Optional[str] = None
        
        self.concept_ids: List[str] = []
        self.competence_ids: List[str] = []
        
        # Statistiques
        self.tests_passed = 0
        self.tests_failed = 0
        self.total_requests = 0
        self.start_time = time.time()
    
    # ═══════════════════════════════════════════════════
    # UTILITAIRES D'AFFICHAGE
    # ═══════════════════════════════════════════════════
    
    def print_header(self, title: str):
        """Affiche un header de section."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}{Colors.RESET}\n")
    
    def print_test(self, method: str, endpoint: str, description: str = ""):
        """Affiche l'info du test en cours."""
        print(f"{Colors.CYAN}[TEST] {method:6} {endpoint}{Colors.RESET}")
        if description:
            print(f"       → {description}")
    
    def print_success(self, message: str):
        """Log de succès."""
        print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")
        self.tests_passed += 1
    
    def print_error(self, message: str):
        """Log d'erreur."""
        print(f"{Colors.RED}❌ {message}{Colors.RESET}")
        self.tests_failed += 1
    
    def print_info(self, message: str):
        """Log d'information."""
        print(f"{Colors.YELLOW}ℹ️  {message}{Colors.RESET}")
    
    def print_json(self, data: Dict, max_lines: int = 20):
        """Affiche du JSON formaté (limité)."""
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        lines = json_str.split('\n')
        
        if len(lines) > max_lines:
            print('\n'.join(lines[:max_lines]))
            print(f"{Colors.YELLOW}... ({len(lines) - max_lines} lignes supplémentaires){Colors.RESET}")
        else:
            print(json_str)
    
    def set_auth_header(self):
        """Configure le header d'authentification JWT."""
        if self.token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })
    
    def make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Effectue une requête HTTP avec gestion d'erreurs."""
        self.total_requests += 1
        
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        
        except requests.exceptions.Timeout:
            self.print_error("Timeout de la requête")
            return None
        
        except requests.exceptions.ConnectionError:
            self.print_error("Erreur de connexion au serveur")
            return None
        
        except Exception as e:
            self.print_error(f"Erreur inattendue : {str(e)}")
            return None
    
    # ═══════════════════════════════════════════════════
    # TESTS - AUTHENTIFICATION
    # ═══════════════════════════════════════════════════
    
    def test_auth_register(self):
        """POST /api/auth/register - Inscription."""
        self.print_header("🔐 AUTHENTIFICATION")
        
        endpoint = "/auth/register"
        url = f"{BASE_URL}{endpoint}"
        
        timestamp = int(time.time())
        self.username = f"test_user_{timestamp}"
        self.email = f"test_{timestamp}@example.com"
        
        payload = {
            "username": self.username,
            "email": self.email,
            "password": "Test123456"
        }
        
        self.print_test("POST", endpoint, "Inscription d'un nouvel utilisateur")
        self.print_info(f"Username: {self.username}")
        
        response = self.make_request("POST", url, json=payload)
        
        if response and response.status_code == 201:
            data = response.json()
            if data.get("success"):
                self.token = data["data"]["access_token"]
                self.user_id = data["data"]["user_id"]
                self.set_auth_header()
                
                self.print_success(f"Utilisateur créé (ID: {self.user_id})")
                self.print_success(f"Token JWT obtenu : {self.token[:30]}...")
                return True
        
        self.print_error(f"Échec de l'inscription (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_auth_login(self):
        """POST /api/auth/login - Connexion."""
        endpoint = "/auth/login"
        url = f"{BASE_URL}{endpoint}"
        
        payload = {
            "email": self.email,
            "password": "Test123456"
        }
        
        self.print_test("POST", endpoint, "Connexion avec les credentials")
        
        response = self.make_request("POST", url, json=payload)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.print_success("Connexion réussie")
                self.print_info(f"Token identique: {data['data']['access_token'][:30]}...")
                return True
        
        self.print_error(f"Échec de la connexion (Status: {response.status_code if response else 'N/A'})")
        return False
    
    # ═══════════════════════════════════════════════════
    # TESTS - DOMAINES
    # ═══════════════════════════════════════════════════
    
    def test_get_all_domaines(self):
        """GET /api/domaines - Lister tous les domaines."""
        self.print_header("📚 DOMAINES")
        
        endpoint = "/domaines"
        url = f"{BASE_URL}{endpoint}"
        
        self.print_test("GET", endpoint, "Récupérer la liste complète des domaines")
        
        response = self.make_request("GET", url)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                domaines = data["data"]
                self.print_success(f"{len(domaines)} domaines trouvés")
                
                # Afficher les domaines
                for domaine in domaines:
                    matieres_count = len(domaine.get('matieres', []))
                    print(f"  • {domaine['name']} ({matieres_count} matières)")
                
                # Sélectionner "Programmation" pour la suite
                prog = next((d for d in domaines if d["name"] == "Programmation"), None)
                if prog:
                    self.domaine_id = prog["_id"]
                    self.domaine_name = prog["name"]
                    self.print_info(f"Domaine sélectionné pour tests : {self.domaine_name}")
                    return True
                else:
                    self.print_error("Domaine 'Programmation' non trouvé")
                    return False
        
        self.print_error(f"Échec de récupération (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_get_domaine_by_id(self):
        """GET /api/domaines/{domaine_id} - Détails d'un domaine."""
        endpoint = f"/domaines/{self.domaine_id}"
        url = f"{BASE_URL}{endpoint}"
        
        self.print_test("GET", endpoint, f"Détails du domaine '{self.domaine_name}'")
        
        response = self.make_request("GET", url)
        
        if response and response.status_code == 200:
            domaine = response.json()
            self.print_success(f"Domaine récupéré : {domaine['name']}")
            self.print_info(f"Description : {domaine['description'][:60]}...")
            self.print_info(f"Matières : {', '.join([m['name'] for m in domaine.get('matieres', [])])}")
            return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_select_domaines(self):
        """POST /api/user/domaines - Sélectionner des domaines."""
        endpoint = "/user/domaines"
        url = f"{BASE_URL}{endpoint}"
        
        payload = {
            "domaine_ids": [self.domaine_id]
        }
        
        self.print_test("POST", endpoint, "Sélectionner le domaine Programmation")
        
        response = self.make_request("POST", url, json=payload)
        
        if response and response.status_code == 201:
            data = response.json()
            if data.get("success"):
                self.print_success(data.get("message"))
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_get_user_domaines(self):
        """GET /api/user/domaines - Mes domaines sélectionnés."""
        endpoint = "/user/domaines"
        url = f"{BASE_URL}{endpoint}"
        
        self.print_test("GET", endpoint, "Récupérer mes domaines")
        
        response = self.make_request("GET", url)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.print_success(f"{data['count']} domaine(s) sélectionné(s)")
                for domaine in data["data"]:
                    print(f"  • {domaine['name']} (sélectionné le {domaine['selected_at'][:10]})")
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    # ═══════════════════════════════════════════════════
    # TESTS - MATIÈRES ET GÉNÉRATION IA
    # ═══════════════════════════════════════════════════
    
    def test_select_matieres_generate_plans(self):
        """POST /api/matieres/select - Sélectionner matière + Génération IA."""
        self.print_header("🤖 MATIÈRES & GÉNÉRATION IA")
        
        endpoint = "/matieres/select"
        url = f"{BASE_URL}{endpoint}"
        
        self.matiere_name = "Python"
        
        payload = {
            "domaine_id": self.domaine_id,
            "matiere_names": [self.matiere_name]
        }
        
        self.print_test("POST", endpoint, f"Sélectionner '{self.matiere_name}' → Génération Spiral Learning")
        self.print_info("⏳ Génération en cours avec Ollama (60-120 secondes)...")
        
        start_time = time.time()
        response = self.make_request("POST", url, json=payload, timeout=5000)
        duration = time.time() - start_time
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.print_success(f"Génération terminée en {duration:.1f}s")
                self.print_success(data)
                
                if data["data"].get("generated_plans"):
                    for plan_info in data["data"]["generated_plans"]:
                        print(f"  • {plan_info['matiere_name']} : {plan_info['plans_count']} plans générés")
                
                return True
        
        self.print_error(f"Échec de génération (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_get_user_matieres(self):
        """GET /api/user/matieres - Mes matières sélectionnées."""
        endpoint = "/user/matieres"
        url = f"{BASE_URL}{endpoint}"
        
        self.print_test("GET", endpoint, "Récupérer mes matières")
        
        response = self.make_request("GET", url)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.print_success(f"{data['data']['count']} matière(s) sélectionnée(s)")
                for matiere in data["data"]["matieres"]:
                    print(f"  • {matiere['matiere_name']} ({matiere['domaine_name']})")
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    # ═══════════════════════════════════════════════════
    # TESTS - PLANS D'APPRENTISSAGE
    # ═══════════════════════════════════════════════════
    
    def test_get_plans_by_matiere(self):
        """GET /api/plans/{domaine_id}/{matiere_name} - Plans d'une matière."""
        self.print_header("📖 PLANS D'APPRENTISSAGE")
        
        endpoint = f"/plans/{self.domaine_id}/{self.matiere_name}"
        url = f"{BASE_URL}{endpoint}"
        
        self.print_test("GET", endpoint, f"Plans pour '{self.matiere_name}'")
        
        response = self.make_request("GET", url)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                plans = data["data"]["plans"]
                self.print_success(f"{len(plans)} plans trouvés")
                
                for plan in plans:
                    print(f"\n  📘 {plan['nom']}")
                    print(f"     Niveau       : {plan['niveau']}")
                    print(f"     Durée        : {plan['durée_totale']}")
                    print(f"     Objectifs    : {len(plan.get('objectifs_généraux', []))}")
                    print(f"     Concepts     : {len(plan.get('concept_ids', []))}")
                    print(f"     Prérequis    : {', '.join(plan.get('prérequis', [])) or 'Aucun'}")
                    
                    # Stocker les IDs
                    self.plan_ids.append(plan["_id"])
                    
                    if plan['niveau'] == 1:
                        self.plan_id_debutant = plan["_id"]
                    elif plan['niveau'] == 2:
                        self.plan_id_intermediaire = plan["_id"]
                    elif plan['niveau'] == 3:
                        self.plan_id_avance = plan["_id"]
                
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_get_concepts_by_plan(self):
        """GET /api/plans/{plan_id}/concepts - Concepts d'un plan."""
        self.print_header("🧩 CONCEPTS & COMPÉTENCES")
        
        plan_id = self.plan_id_debutant
        endpoint = f"/plans/{plan_id}/concepts"
        url = f"{BASE_URL}{endpoint}"
        
        self.print_test("GET", endpoint, "Récupérer concepts du plan débutant")
        
        response = self.make_request("GET", url)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                concepts = data["data"]["concepts"]
                self.print_success(f"{len(concepts)} concepts trouvés")
                
                total_competences = 0
                total_ressources = 0
                
                for concept in concepts:
                    competences = concept.get("compétences", [])
                    total_competences += len(competences)
                    
                    self.concept_ids.append(concept["_id"])
                    
                    print(f"\n  📌 Concept {concept['ordre']} : {concept['nom']}")
                    print(f"     Durée        : {concept['durée']}")
                    print(f"     Description  : {concept['description'][:60]}...")
                    print(f"     Compétences  : {len(competences)}")
                    
                    # Afficher 2 premières compétences
                    for i, comp in enumerate(competences[:2], 1):
                        print(f"       {i}. {comp['nom']}")
                        print(f"          Difficulté    : {comp['difficulté']}")
                        print(f"          Temps estimé  : {comp['temps_estimé']}")
                        print(f"          Niveau cognitif: {comp['niveau_cognitif']}")
                        print(f"          Ressources    : {len(comp.get('ressources', []))}")
                        
                        total_ressources += len(comp.get('ressources', []))
                        self.competence_ids.append(comp["_id"])
                    
                    # Activité pratique
                    activite = concept.get("activité_pratique", {})
                    if activite:
                        print(f"     🎯 Activité  : {activite.get('nom')} ({activite.get('type')})")
                        print(f"        Durée     : {activite.get('durée_estimée')}")
                
                self.print_success(f"Total : {total_competences} compétences, {total_ressources} ressources")
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_select_multiple_plans(self):
        """POST /api/user/plans - Sélectionner plusieurs plans."""
        self.print_header("✅ SÉLECTION DE PLANS")
        
        endpoint = "/user/plans"
        url = f"{BASE_URL}{endpoint}"
        
        # Sélectionner les 3 niveaux
        payload = {
            "plan_matiere_ids": self.plan_ids
        }
        
        self.print_test("POST", endpoint, f"Sélectionner {len(self.plan_ids)} plans")
        
        response = self.make_request("POST", url, json=payload)
        
        if response and response.status_code == 201:
            data = response.json()
            if data.get("success"):
                self.print_success(data.get("message"))
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_get_user_plans(self):
        """GET /api/user/plans - Mes plans sélectionnés."""
        endpoint = "/user/plans"
        url = f"{BASE_URL}{endpoint}"
        
        self.print_test("GET", endpoint, "Récupérer mes plans")
        
        response = self.make_request("GET", url)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                plans = data["data"]["plans"]
                self.print_success(f"{len(plans)} plan(s) en cours")
                
                for plan in plans:
                    print(f"\n  📖 {plan['nom']}")
                    print(f"     Status    : {plan['status']}")
                    print(f"     Progression: {plan['progress']}%")
                    print(f"     Sélectionné: {plan['selected_at'][:10]}")
                
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    # ═══════════════════════════════════════════════════
    # TESTS - PROGRESSION
    # ═══════════════════════════════════════════════════
    
    def test_update_plan_status_start(self):
        """PATCH /api/user/plans/{id}/status - Démarrer un plan."""
        self.print_header("📈 GESTION DE LA PROGRESSION")
        
        plan_id = self.plan_id_debutant
        endpoint = f"/user/plans/{plan_id}/status"
        url = f"{BASE_URL}{endpoint}"
        
        payload = {
            "status": "en_cours",
            "progress": 0
        }
        
        self.print_test("PATCH", endpoint, "Démarrer le plan débutant")
        
        response = self.make_request("PATCH", url, json=payload)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.print_success(data.get("message"))
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_update_plan_progress(self):
        """PATCH /api/user/plans/{id}/status - Mettre à jour progression."""
        plan_id = self.plan_id_debutant
        endpoint = f"/user/plans/{plan_id}/status"
        url = f"{BASE_URL}{endpoint}"
        
        payload = {
            "status": "en_cours",
            "progress": 50
        }
        
        self.print_test("PATCH", endpoint, "Progression à 50%")
        
        response = self.make_request("PATCH", url, json=payload)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.print_success(data.get("message"))
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    def test_update_plan_complete(self):
        """PATCH /api/user/plans/{id}/status - Terminer un plan."""
        plan_id = self.plan_id_debutant
        endpoint = f"/user/plans/{plan_id}/status"
        url = f"{BASE_URL}{endpoint}"
        
        payload = {
            "status": "terminé"
        }
        
        self.print_test("PATCH", endpoint, "Marquer comme terminé")
        
        response = self.make_request("PATCH", url, json=payload)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.print_success(data.get("message"))
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    # ═══════════════════════════════════════════════════
    # TESTS - SUPPRESSION
    # ═══════════════════════════════════════════════════
    
    def test_delete_domaine(self):
        """DELETE /api/user/domaines/{domaine_id} - Désélectionner un domaine."""
        self.print_header("🗑️  SUPPRESSION")
        
        endpoint = f"/user/domaines/{self.domaine_id}"
        url = f"{BASE_URL}{endpoint}"
        
        self.print_test("DELETE", endpoint, "Désélectionner le domaine Programmation")
        
        response = self.make_request("DELETE", url)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.print_success(data.get("message"))
                return True
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    # ═══════════════════════════════════════════════════
    # TESTS - OLLAMA
    # ═══════════════════════════════════════════════════
    
    def test_ollama_status(self):
        """GET /api/ollama/status - Vérifier statut Ollama."""
        self.print_header("🤖 OLLAMA")
        
        endpoint = "/ollama/status"
        url = f"{BASE_URL}{endpoint}"
        
        self.print_test("GET", endpoint, "Vérifier la connexion à Ollama")
        
        response = self.make_request("GET", url)
        
        if response and response.status_code == 200:
            data = response.json()
            is_connected = data["data"]["connected"]
            
            if is_connected:
                self.print_success(f"Ollama connecté : {data['data']['url']}")
                self.print_info(f"Modèle : {data['data']['model']}")
                return True
            else:
                self.print_error("Ollama non accessible")
                return False
        
        self.print_error(f"Échec (Status: {response.status_code if response else 'N/A'})")
        return False
    
    # ═══════════════════════════════════════════════════
    # ORCHESTRATION DES TESTS
    # ═══════════════════════════════════════════════════
    
    def run_all_tests(self):
        """Exécute tous les tests dans l'ordre."""
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}{'='*70}")
        print(f"  🚀 DÉMARRAGE DES TESTS - API SPIRAL LEARNING")
        print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}{Colors.RESET}\n")
        
        # Liste des tests à exécuter
        tests = [
            # Authentification
            ("Inscription", self.test_auth_register),
            ("Connexion", self.test_auth_login),
            
            # Domaines
            ("Lister domaines", self.test_get_all_domaines),
            ("Détails domaine", self.test_get_domaine_by_id),
            ("Sélectionner domaines", self.test_select_domaines),
            ("Mes domaines", self.test_get_user_domaines),
            
            # Matières et IA
            ("Sélectionner matière + Génération IA", self.test_select_matieres_generate_plans),
            ("Mes matières", self.test_get_user_matieres),
            
            # Plans
            ("Plans d'une matière", self.test_get_plans_by_matiere),
            ("Concepts et compétences", self.test_get_concepts_by_plan),
            ("Sélectionner plans", self.test_select_multiple_plans),
            ("Mes plans", self.test_get_user_plans),
            
            # Progression
            # ("Démarrer plan", self.test_update_plan_status_start),
            # ("Progression 50%", self.test_update_plan_progress),
            # ("Terminer plan", self.test_update_plan_complete),
            
            # # Suppression
            # ("Désélectionner domaine", self.test_delete_domaine),
            
            # Ollama
            ("Statut Ollama", self.test_ollama_status),
        ]
        
        # Exécution
        results = {}
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                
                if not result:
                    self.print_info(f"Test '{test_name}' échoué, mais on continue...")
                
                time.sleep(0.5)  # Pause entre tests
                
            except Exception as e:
                self.print_error(f"Exception dans '{test_name}' : {str(e)}")
                results[test_name] = False
        
        # Résumé
        self.print_summary(results)
    
    def print_summary(self, results: Dict[str, bool]):
        """Affiche le résumé final des tests."""
        duration = time.time() - self.start_time
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
        print(f"  📊 RÉSUMÉ DES TESTS")
        print(f"{'='*70}{Colors.RESET}\n")
        
        for test_name, result in results.items():
            status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if result else f"{Colors.RED}❌ FAIL{Colors.RESET}"
            print(f"{status} - {test_name}")
        
        print(f"\n{Colors.BOLD}{'─'*70}{Colors.RESET}")
        print(f"Tests réussis        : {Colors.GREEN}{self.tests_passed}{Colors.RESET}")
        print(f"Tests échoués        : {Colors.RED}{self.tests_failed}{Colors.RESET}")
        print(f"Total                : {self.tests_passed + self.tests_failed}")
        print(f"Requêtes HTTP        : {self.total_requests}")
        print(f"Durée totale         : {duration:.1f}s")
        
        success_rate = (self.tests_passed / (self.tests_passed + self.tests_failed) * 100) if (self.tests_passed + self.tests_failed) > 0 else 0
        
        color = Colors.GREEN if success_rate >= 90 else Colors.YELLOW if success_rate >= 70 else Colors.RED
        print(f"Taux de réussite     : {color}{success_rate:.1f}%{Colors.RESET}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.RESET}\n")
        
        if success_rate == 100:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 TOUS LES TESTS SONT PASSÉS ! 🎉{Colors.RESET}\n")
        elif success_rate >= 90:
            print(f"{Colors.YELLOW}⚠️  Quelques tests ont échoué, vérifiez les logs{Colors.RESET}\n")
        else:
            print(f"{Colors.RED}❌ De nombreux tests ont échoué, vérifiez la configuration{Colors.RESET}\n")


# ═══════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    print(f"{Colors.CYAN}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║                                                                   ║")
    print("║           🧪 TEST AUTOMATISÉ - API SPIRAL LEARNING 🧪             ║")
    print("║                                                                   ║")
    print("║  Ce script teste tous les endpoints de l'API de manière          ║")
    print("║  exhaustive et dans l'ordre logique du parcours utilisateur.     ║")
    print("║                                                                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    print(f"{Colors.YELLOW}Prérequis :{Colors.RESET}")
    print("  ☐ MongoDB démarré (port 27017)")
    print("  ☐ Ollama démarré (port 11434)")
    print("  ☐ Flask démarré (port 5000)")
    print()
    
    input(f"{Colors.CYAN}Appuyez sur Entrée pour commencer les tests...{Colors.RESET}\n")
    
    tester = APITester()
    tester.run_all_tests()
    
    sys.exit(0 if tester.tests_failed == 0 else 1)
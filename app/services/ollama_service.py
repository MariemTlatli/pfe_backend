"""
Service Ollama - Interface avec le modèle GenAI local.
"""

import requests
import json
import re
from app.config import Config


class OllamaService:
    """Interface pour communiquer avec Ollama (LLM local)."""
    
    BASE_URL = Config.OLLAMA_BASE_URL
    MODEL = Config.OLLAMA_MODEL
    TIMEOUT = Config.OLLAMA_TIMEOUT
    
    @staticmethod
    def generate(prompt, temperature=None, max_tokens=4000, system_prompt=None):
        """
        Générer du contenu avec Ollama.
        
        Args:
            prompt (str): Le prompt utilisateur
            temperature (float, optional): Créativité (0-1)
            max_tokens (int): Nombre max de tokens
            system_prompt (str, optional): Instructions système
            
        Returns:
            str: Réponse du modèle
            
        Raises:
            Exception: Si erreur de communication
        """
        url = f"{OllamaService.BASE_URL}/api/generate"
        
        if temperature is None:
            temperature = Config.OLLAMA_TEMPERATURE
        
        payload = {
            "model": OllamaService.MODEL,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=OllamaService.TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('response', '').strip()
        
        except requests.exceptions.Timeout:
            raise Exception(f"Timeout: Ollama n'a pas répondu en {OllamaService.TIMEOUT}s")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Impossible de se connecter à Ollama sur {OllamaService.BASE_URL}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Erreur HTTP Ollama: {e}")
        except Exception as e:
            raise Exception(f"Erreur Ollama: {str(e)}")
    
    @staticmethod
    def generate_json(prompt, system_prompt=None, temperature=0.3):
        """
        Générer une réponse JSON structurée.
        
        Args:
            prompt (str): Le prompt
            system_prompt (str, optional): Instructions système
            temperature (float): Faible pour plus de cohérence
            
        Returns:
            dict: Données JSON parsées
            
        Raises:
            ValueError: Si le JSON est invalide
        """
        if system_prompt is None:
            system_prompt = (
                "Tu es un assistant qui répond UNIQUEMENT en JSON valide. "
                "Ne pas ajouter de texte avant ou après le JSON. "
                "Pas de markdown, juste du JSON brut."
            )
        
        response_text = OllamaService.generate(
            prompt,
            temperature=temperature,
            system_prompt=system_prompt
        )
        
        # Nettoyer la réponse (parfois Ollama ajoute des balises markdown)
        response_text = response_text.strip()
        
        # Retirer les balises markdown si présentes
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Normaliser les caractères de contrôle invalides dans les chaînes
        # Remplacer les vraies ruptures de ligne par \n échappé
        response_text = OllamaService._normalize_json_string(response_text)
        
        # Première tentative de parsing
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as first_exc:
            # essayer de réparer quelques fautes courantes (virgules manquantes, etc.)
            repaired = OllamaService._repair_json(response_text)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as second_exc:
                raise ValueError(
                    f"Réponse JSON invalide: {second_exc}\n\n"
                    f"Texte original :\n{response_text}\n\n"
                    f"Texte réparé   :\n{repaired}"
                )
    
    @staticmethod
    def _normalize_json_string(text):
        """
        Normaliser une chaîne brute JSON en échappant correctement les caractères de contrôle.
        
        Cela corrige les cas où Ollama retourne du JSON avec des vraies ruptures de ligne
        au lieu de \n échappé dans les chaînes de caractères.
        
        Args:
            text (str): Texte JSON brut potentiellement mal formé
            
        Returns:
            str: Texte JSON normalisé et valide
        """
        result = []
        in_string = False
        escape_next = False
        i = 0
        
        while i < len(text):
            char = text[i]
            
            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue
            
            if char == '\\' and in_string:
                result.append(char)
                escape_next = True
                i += 1
                continue
            
            if char == '"':
                in_string = not in_string
                result.append(char)
                i += 1
                continue
            
            # Si on est dans une string et qu'on rencontre un caractère de contrôle
            if in_string:
                if char == '\n':
                    result.append('\\n')
                    i += 1
                    continue
                elif char == '\r':
                    result.append('\\r')
                    i += 1
                    continue
                elif char == '\t':
                    result.append('\\t')
                    i += 1
                    continue
                elif ord(char) < 32:  # Autres caractères de contrôle
                    result.append(f'\\u{ord(char):04x}')
                    i += 1
                    continue
            
            result.append(char)
            i += 1
        
        return ''.join(result)
    
    @staticmethod
    def _repair_json(text):
        """
        Appliquer des heuristiques légères pour tenter de réparer du JSON
        généré par le modèle lorsqu'il manque une virgule ou présente une
        syntaxe légèrement incorrecte.
        """
        # insérer une virgule entre deux objets/tableaux adjacents (}{, ][) sans
        # virgule
        repaired = re.sub(r'(?<=[\}\]])\s*(?=[\{\[])', ', ', text)
        # supprimer les virgules superflues avant ] ou }
        repaired = re.sub(r',\s*(?=[\}\]])', '', repaired)
        return repaired
    
    @staticmethod
    def is_available():
        """
        Vérifier si Ollama est accessible.
        
        Returns:
            bool: True si disponible
        """
        try:
            response = requests.get(
                f"{OllamaService.BASE_URL}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def get_models():
        """
        Lister les modèles disponibles.
        
        Returns:
            list: Liste des modèles
        """
        try:
            response = requests.get(
                f"{OllamaService.BASE_URL}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except:
            return []
"""
Validateurs personnalisés pour l'application.
"""

from bson import ObjectId
from bson.errors import InvalidId
import re
import json


def validate_objectid(value):
    """
    Valider qu'une chaîne est un ObjectId MongoDB valide.
    
    Args:
        value (str): Chaîne à valider
        
    Returns:
        bool: True si valide
        
    Raises:
        ValueError: Si invalide
    """
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        raise ValueError(f"'{value}' n'est pas un ObjectId MongoDB valide")


def validate_code_format(code, pattern=r'^[A-Z]{3}\d{3}$'):
    """
    Valider le format d'un code de compétence.
    
    Args:
        code (str): Code à valider (ex: "VAR001")
        pattern (str): Pattern regex (défaut: 3 lettres + 3 chiffres)
        
    Returns:
        bool: True si valide
        
    Raises:
        ValueError: Si format invalide
    
    Examples:
        >>> validate_code_format("VAR001")  # ✅ True
        >>> validate_code_format("var001")  # ❌ ValueError
        >>> validate_code_format("VARIA1")  # ❌ ValueError
    """
    if not re.match(pattern, code):
        raise ValueError(
            f"Code '{code}' invalide. Format attendu: 3 lettres majuscules + 3 chiffres (ex: VAR001)"
        )
    return True


def validate_json_structure(data, required_keys):
    """
    Valider qu'un dict/JSON contient les clés requises.
    
    Args:
        data (dict): Données à valider
        required_keys (list): Liste des clés obligatoires
        
    Returns:
        bool: True si valide
        
    Raises:
        ValueError: Si clés manquantes
    
    Examples:
        >>> validate_json_structure({"name": "Test"}, ["name"])  # ✅ True
        >>> validate_json_structure({"name": "Test"}, ["name", "age"])  # ❌ ValueError
    """
    if not isinstance(data, dict):
        raise ValueError("Les données doivent être un dictionnaire")
    
    missing_keys = [key for key in required_keys if key not in data]
    
    if missing_keys:
        raise ValueError(f"Clés manquantes: {', '.join(missing_keys)}")
    
    return True


def validate_bkt_params(params):
    """
    Valider les paramètres BKT (probabilités entre 0 et 1).
    
    Args:
        params (dict): Paramètres BKT
        
    Returns:
        bool: True si valide
        
    Raises:
        ValueError: Si paramètres invalides
    """
    required_keys = ['p_know', 'p_learn', 'p_guess', 'p_slip']
    validate_json_structure(params, required_keys)
    
    for key, value in params.items():
        if key in required_keys:
            if not isinstance(value, (int, float)):
                raise ValueError(f"{key} doit être un nombre")
            if not 0 <= value <= 1:
                raise ValueError(f"{key} doit être entre 0 et 1 (reçu: {value})")
    
    return True


def validate_graph_data(graph_data):
    """
    Valider les données de position du graphe.
    
    Args:
        graph_data (dict): Données de position {x, y}
        
    Returns:
        bool: True si valide
        
    Raises:
        ValueError: Si format invalide
    """
    if not isinstance(graph_data, dict):
        raise ValueError("graph_data doit être un dictionnaire")
    
    if 'x' not in graph_data or 'y' not in graph_data:
        raise ValueError("graph_data doit contenir 'x' et 'y'")
    
    if not isinstance(graph_data['x'], (int, float)):
        raise ValueError("x doit être un nombre")
    
    if not isinstance(graph_data['y'], (int, float)):
        raise ValueError("y doit être un nombre")
    
    return True


def sanitize_input(text, max_length=1000):
    """
    Nettoyer une entrée utilisateur (prévention XSS basique).
    
    Args:
        text (str): Texte à nettoyer
        max_length (int): Longueur maximale
        
    Returns:
        str: Texte nettoyé
    """
    if not isinstance(text, str):
        return ""
    
    # Retirer les caractères dangereux
    text = text.strip()
    text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<.*?>', '', text)  # Retirer balises HTML
    
    # Limiter la longueur
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_level(level, min_level=1, max_level=5):
    """
    Valider un niveau de difficulté.
    
    Args:
        level (int): Niveau à valider
        min_level (int): Niveau minimum
        max_level (int): Niveau maximum
        
    Returns:
        bool: True si valide
        
    Raises:
        ValueError: Si niveau invalide
    """
    if not isinstance(level, int):
        raise ValueError("Le niveau doit être un entier")
    
    if not min_level <= level <= max_level:
        raise ValueError(f"Le niveau doit être entre {min_level} et {max_level}")
    
    return True
from flask import send_file
from marshmallow import Schema, fields
import os

class GraphImageResponseSchema(Schema):
    """Schéma de réponse pour l'image du graphe."""
    message = fields.String()
    file_path = fields.String()
    file_url = fields.String()
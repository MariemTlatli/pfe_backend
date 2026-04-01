"""
Schémas Marshmallow pour validation des données.
"""

from app.schemas.domain import DomainSchema, DomainCreateSchema, DomainUpdateSchema
from app.schemas.subject import SubjectSchema, SubjectCreateSchema, SubjectUpdateSchema
from app.schemas.competence import CompetenceSchema
from app.schemas.lesson import LessonSchema, LessonCreateSchema
from app.schemas.common import MessageSchema, ErrorSchema, PaginationSchema

__all__ = [
    'DomainSchema', 'DomainCreateSchema', 'DomainUpdateSchema',
    'SubjectSchema', 'SubjectCreateSchema', 'SubjectUpdateSchema',
    'CompetenceSchema',
    'LessonSchema', 'LessonCreateSchema',
    'MessageSchema', 'ErrorSchema', 'PaginationSchema'
]
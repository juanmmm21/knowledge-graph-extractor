"""Compatibilidad: el código vive en el paquete `knowledge_graph_extractor`. Este módulo se
conserva para quien añade esta carpeta a `sys.path` e importa `extractor`
directamente."""

from knowledge_graph_extractor.extractor import *  # noqa: F401,F403
from knowledge_graph_extractor.extractor import Entity, Relation, KnowledgeGraph, KnowledgeGraphExtractor  # noqa: F401

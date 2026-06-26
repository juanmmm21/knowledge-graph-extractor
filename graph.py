import json
import os
import logging
from typing import Dict, List, Set, Union
from extractor import Entity, Relation, KnowledgeGraph

logger = logging.getLogger(__name__)

class KnowledgeGraphStore:
    """
    Almacenamiento y gestor en memoria para grafos de conocimiento.
    
    Provee mecanismos para consolidar multiples extracciones de texto,
    ejecutar resolucion de entidades (fusiòn de nodos duplicados),
    guardar/cargar de disco en JSON y exportar a scripts Cypher de Neo4j.
    """
    
    def __init__(self) -> None:
        # Almacenamos entidades indexadas por su version normalizada (en minusculas)
        self.entities: Dict[str, Entity] = {}
        # Lista de relaciones direccionales unificadas
        self.relations: List[Relation] = []

    def _normalize_name(self, name: str) -> str:
        """
        Normaliza el nombre de una entidad para agrupar variaciones de escritura.
        Quita espacios en blanco innecesarios y convierte a minusculas.
        """
        return name.strip().lower()

    def add_entity(self, entity: Entity) -> None:
        """
        Agrega una entidad al almacen. Si la entidad ya existe (por coincidencia de nombre
        normalizado), ejecuta una fusion de metadatos (Entity Resolution) combinando
        las descripciones y actualizando tipos si es necesario.
        """
        norm_name = self._normalize_name(entity.name)
        
        if norm_name not in self.entities:
            # Si no existe, la creamos y guardamos la capitalizacion original
            # Hacemos una copia para evitar mutaciones externas inesperadas
            self.entities[norm_name] = Entity(
                name=entity.name.strip(),
                type=entity.type.strip().upper(),
                description=entity.description.strip()
            )
        else:
            existing = self.entities[norm_name]
            
            # Resolucion: Conservamos el nombre con mejor capitalizacion (la mas larga)
            if len(entity.name.strip()) > len(existing.name):
                existing.name = entity.name.strip()
                
            # Resolucion: Si el tipo existente es generico ('CONCEPT'), lo actualizamos a uno especifico
            if existing.type == "CONCEPT" and entity.type.strip().upper() != "CONCEPT":
                existing.type = entity.type.strip().upper()
                
            # Resolucion: Fusionamos las descripciones de forma limpia evitando duplicados
            desc_existing = existing.description.strip()
            desc_new = entity.description.strip()
            if desc_new and desc_new not in desc_existing:
                existing.description = f"{desc_existing} | {desc_new}"

    def add_relation(self, relation: Relation) -> None:
        """
        Agrega una relacion al grafo. Valida que las entidades origen y destino existan,
        aplica unificacion de nombres, y resuelve duplicados de aristas.
        """
        norm_src = self._normalize_name(relation.source)
        norm_tgt = self._normalize_name(relation.target)
        
        # Garantizamos que las entidades implicadas esten indexadas en el grafo.
        # Si no estan, las agregamos con datos basicos por defecto.
        if norm_src not in self.entities:
            self.add_entity(Entity(name=relation.source, type="CONCEPT", description="Entidad inferida implicitamente por relacion"))
        if norm_tgt not in self.entities:
            self.add_entity(Entity(name=relation.target, type="CONCEPT", description="Entidad inferida implicitamente por relacion"))
            
        # Resolvemos los nombres con las versiones unificadas del almacen
        src_entity = self.entities[norm_src]
        tgt_entity = self.entities[norm_tgt]
        
        rel_type = relation.type.strip().upper()
        rel_desc = relation.description.strip()
        
        # Comprobamos si ya existe exactamente la misma relacion (origen, destino, tipo)
        duplicate_found = False
        for r in self.relations:
            if (self._normalize_name(r.source) == norm_src and 
                self._normalize_name(r.target) == norm_tgt and 
                r.type == rel_type):
                # Si existe, fusionamos las explicaciones de la relacion
                if rel_desc and rel_desc not in r.description:
                    r.description = f"{r.description} | {rel_desc}"
                duplicate_found = True
                break
                
        if not duplicate_found:
            self.relations.append(Relation(
                source=src_entity.name,
                target=tgt_entity.name,
                type=rel_type,
                description=rel_desc
            ))

    def add_graph(self, graph: KnowledgeGraph) -> None:
        """
        Consolida un grafo completo extraido (entidades y relaciones) dentro del almacen.
        """
        for entity in graph.entities:
            self.add_entity(entity)
        for relation in graph.relations:
            self.add_relation(relation)

    def to_dict(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Exporta el grafo de conocimiento a un diccionario plano.
        """
        return {
            "entities": [e.model_dump() for e in self.entities.values()],
            "relations": [r.model_dump() for r in self.relations]
        }

    def save_to_json(self, filepath: str) -> None:
        """
        Persiste el grafo estructurado en disco en formato JSON legible.
        """
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Grafo de conocimiento guardado exitosamente en {filepath}")
        except Exception as e:
            logger.error(f"Error al guardar grafo en {filepath}: {str(e)}")
            raise

    def load_from_json(self, filepath: str) -> None:
        """
        Carga y une un grafo de conocimiento persistido en disco.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"No se encontro el archivo de grafo en: {filepath}")
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Limpiamos el estado actual antes de la carga
            self.entities.clear()
            self.relations.clear()
            
            # Cargamos entidades
            for e_data in data.get("entities", []):
                self.add_entity(Entity(**e_data))
            # Cargamos relaciones
            for r_data in data.get("relations", []):
                self.add_relation(Relation(**r_data))
                
            logger.info(f"Grafo cargado exitosamente desde {filepath} ({len(self.entities)} entidades, {len(self.relations)} relaciones)")
        except Exception as e:
            logger.error(f"Error al cargar el grafo desde {filepath}: {str(e)}")
            raise

    def to_neo4j_cypher(self) -> str:
        """
        Genera una secuencia de comandos Cypher para cargar el grafo de conocimiento completo
        en una base de datos Neo4j mediante operaciones seguras MERGE.
        """
        def escape(s: str) -> str:
            return s.replace("'", "\\'")
            
        cypher_lines = ["// --- NEO4J KNOWLEDGE GRAPH EXPORT ---"]
        
        # 1. Creacion de Nodos (Entidades)
        cypher_lines.append("\n// 1. Crear Nodos")
        for ent in self.entities.values():
            name_esc = escape(ent.name)
            desc_esc = escape(ent.description)
            type_esc = escape(ent.type)
            
            # Usamos MERGE para evitar la creacion de duplicados
            # Si el nodo ya existe, agregamos la descripcion nueva como un append
            cypher_line = (
                f"MERGE (n:`{type_esc}` {{name: '{name_esc}'}}) "
                f"ON CREATE SET n.description = '{desc_esc}' "
                f"ON MATCH SET n.description = n.description + ' | ' + '{desc_esc}';"
            )
            cypher_lines.append(cypher_line)
            
        # 2. Creacion de Relaciones
        cypher_lines.append("\n// 2. Crear Relaciones")
        for rel in self.relations:
            src_esc = escape(rel.source)
            tgt_esc = escape(rel.target)
            type_esc = escape(rel.type)
            desc_esc = escape(rel.description)
            
            # Buscamos ambos nodos por nombre independientemente de sus tipos dinamicos y creamos relacion
            cypher_line = (
                f"MATCH (src {{name: '{src_esc}'}}) "
                f"MATCH (tgt {{name: '{tgt_esc}'}}) "
                f"MERGE (src)-[r:`{type_esc}`]->(tgt) "
                f"ON CREATE SET r.description = '{desc_esc}' "
                f"ON MATCH SET r.description = r.description + ' | ' + '{desc_esc}';"
            )
            cypher_lines.append(cypher_line)
            
        return "\n".join(cypher_lines)

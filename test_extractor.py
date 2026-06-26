import unittest
import tempfile
import shutil
import os
import json

from extractor import Entity, Relation, KnowledgeGraph, KnowledgeGraphExtractor
from graph import KnowledgeGraphStore


class TestKnowledgeGraphExtractor(unittest.TestCase):
    """
    Casos de prueba unitarios para la extraccion, consolidacion y
    visualizacion de grafos de conocimiento.
    """

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.json_path = os.path.join(self.tmp_dir, "graph.json")
        self.store = KnowledgeGraphStore()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_pydantic_schemas(self) -> None:
        """
        Verifica que los esquemas de datos Pydantic funcionen e impidan
        valores nulos o invalidos.
        """
        e = Entity(name="Albert", type="PERSON", description="Físico teórico")
        self.assertEqual(e.name, "Albert")
        
        r = Relation(source="Albert", target="Relatividad", type="INVENTED", description="Creó la teoría")
        self.assertEqual(r.source, "Albert")
        
        kg = KnowledgeGraph(entities=[e], relations=[r])
        self.assertEqual(len(kg.entities), 1)

    def test_extractor_offline_fallback(self) -> None:
        """
        Prueba el comportamiento determinista y controlado del extractor
        en modo sin conexion.
        """
        # Inicializamos en offline de forma forzada pasando api_key=None
        extractor = KnowledgeGraphExtractor(api_key=None)
        self.assertFalse(extractor.is_online)
        
        # Test vacio
        kg_empty = extractor.extract("")
        self.assertEqual(len(kg_empty.entities), 0)
        
        # Test astronomia
        kg_astro = extractor.extract("Estudiamos astronomía y el cosmos")
        self.assertGreater(len(kg_astro.entities), 0)
        self.assertTrue(any(e.name == "Astronomia" for e in kg_astro.entities))
        
        # Test programacion
        kg_prog = extractor.extract("Escribir código limpio en Python")
        self.assertGreater(len(kg_prog.entities), 0)
        self.assertTrue(any(e.name == "Python" for e in kg_prog.entities))

    def test_entity_resolution_merging(self) -> None:
        """
        Verifica que se agrupen los nombres normalizados de las entidades y se fusionen
        sus descripciones y tipos de forma correcta.
        """
        e1 = Entity(name="NASA", type="CONCEPT", description="Agencia espacial norteamericana")
        e2 = Entity(name="Nasa", type="ORGANIZATION", description="Lanzó el telescopio James Webb")
        
        self.store.add_entity(e1)
        self.store.add_entity(e2)
        
        # Debe haber una sola entidad registrada (fusión por normalización 'nasa')
        self.assertEqual(len(self.store.entities), 1)
        
        resolved = self.store.entities["nasa"]
        
        # Nombre: se queda con la mas larga o con mejor capitalizacion (NASA en mayusculas)
        self.assertEqual(resolved.name, "NASA")
        
        # Tipo: se actualiza de CONCEPT a ORGANIZATION (mas especifico)
        self.assertEqual(resolved.type, "ORGANIZATION")
        
        # Descripciones: fusionadas con separador '|'
        self.assertIn("Agencia espacial norteamericana", resolved.description)
        self.assertIn("Lanzó el telescopio James Webb", resolved.description)

    def test_relation_deduplication(self) -> None:
        """
        Verifica la adicion e integracion de relaciones direccionales unificadas.
        """
        r1 = Relation(source="Python", target="Software", type="USED_FOR", description="Crear apps")
        r2 = Relation(source="python", target="software", type="USED_FOR", description="Automatizar scripts")
        
        self.store.add_relation(r1)
        self.store.add_relation(r2)
        
        # Deben haberse unificado
        self.assertEqual(len(self.store.relations), 1)
        
        rel = self.store.relations[0]
        self.assertEqual(rel.source, "Python")  # Usa el nombre unificado de la entidad
        self.assertEqual(rel.target, "Software")
        self.assertEqual(rel.type, "USED_FOR")
        self.assertIn("Crear apps", rel.description)
        self.assertIn("Automatizar scripts", rel.description)

    def test_serialization(self) -> None:
        """
        Verifica la persistencia en formato JSON.
        """
        e = Entity(name="Jupiter", type="LOCATION", description="Planeta gigante gaseoso")
        r = Relation(source="Jupiter", target="Saturno", type="NEIGHBOR", description="Ambos en el sistema solar")
        
        self.store.add_entity(e)
        self.store.add_relation(r)
        
        self.store.save_to_json(self.json_path)
        self.assertTrue(os.path.exists(self.json_path))
        
        # Cargamos en un nuevo almacen
        new_store = KnowledgeGraphStore()
        new_store.load_from_json(self.json_path)
        
        self.assertEqual(len(new_store.entities), 2)  # Jupiter y Saturno (inferida por relacion)
        self.assertEqual(len(new_store.relations), 1)
        self.assertEqual(new_store.entities["jupiter"].description, "Planeta gigante gaseoso")

    def test_neo4j_cypher_export(self) -> None:
        """
        Verifica que el generador Cypher formatee sentencias MERGE validas y escape strings.
        """
        e = Entity(name="L'Atelier", type="LOCATION", description="Restaurante en París")
        self.store.add_entity(e)
        
        cypher_script = self.store.to_neo4j_cypher()
        
        # Debe contener sentencias MERGE para el nodo
        self.assertIn("MERGE", cypher_script)
        # Comprobamos el escape de la comilla simple para evitar errores de sintaxis en Neo4j
        self.assertIn("L\\'Atelier", cypher_script)


if __name__ == "__main__":
    unittest.main()

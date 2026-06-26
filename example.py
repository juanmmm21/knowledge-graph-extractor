import os
import sys
import logging
from typing import List

from extractor import KnowledgeGraphExtractor
from graph import KnowledgeGraphStore
from visualizer import GraphVisualizer

# Configuración básica de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Intentamos importar dinámicamente el semantic-chunking-engine de los proyectos vecinos (Interlinking)
sys.path.append(os.path.abspath("../semantic-chunking-engine"))
CHUNKER_AVAILABLE = False
chunker = None

try:
    from chunker import SemanticChunker
    from embedding_provider import MockEmbeddingProvider
    
    # Inicializamos el chunker semántico usando el proveedor Mock local para no requerir descargas pesadas
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(embedding_provider=provider, max_tokens=150)
    CHUNKER_AVAILABLE = True
    logger.info("Interlinking exitoso: cargado SemanticChunker desde 'semantic-chunking-engine'.")
except (ImportError, ModuleNotFoundError):
    logger.info("SemanticChunker no detectado en directorios hermanos. Fallback a segmentación por párrafos.")


def main() -> None:
    print("==================================================")
    print("      Demostración de Knowledge Graph Extractor   ")
    print("==================================================")
    
    # Texto de prueba que describe hitos, personajes e instituciones científicas interconectadas
    text_corpus = (
        "La historia de la ciencia moderna comenzó con Galileo Galilei en Italia, quien desafió las "
        "teorías antiguas observando las lunas de Júpiter con un telescopio casero. Años más tarde, "
        "Isaac Newton en Inglaterra unificó las leyes físicas terrenales y celestes en su teoría de "
        "la gravitación universal, fundando las bases de la física clásica.\n\n"
        "A principios del siglo XX, Albert Einstein en Alemania propuso la teoría de la relatividad general, "
        "demostrando que la gravedad es la curvatura del espacio-tiempo. Einstein colaboró conceptualmente con "
        "varios físicos de su época, aunque rechazó inicialmente la naturaleza probabilística de la mecánica "
        "cuántica naciente.\n\n"
        "La física cuántica se consolidó con científicos como Richard Feynman en Estados Unidos, quien desarrolló "
        "los diagramas de Feynman para simplificar las interacciones de partículas elementales en la electrodinámica "
        "cuántica. Feynman también concibió la idea de la computación cuántica, argumentando que simular la "
        "naturaleza requiere ordenadores que funcionen bajo las leyes de la física cuántica.\n\n"
        "Hoy en día, instituciones internacionales como la NASA exploran el universo profundo usando satélites "
        "y telescopios espaciales, mientras que el CERN en Suiza colisiona partículas en el gran colisionador de "
        "hadrones para descifrar las fuerzas fundamentales descritas por la física cuántica."
    )
    
    # 1. Segmentación del corpus
    chunks: List[str] = []
    if CHUNKER_AVAILABLE and chunker is not None:
        print("\nSegmentando el corpus semánticamente usando el modulo sibling 'semantic-chunking-engine'...")
        chunk_dicts = chunker.chunk_text(text_corpus)
        chunks = [c["text"] for c in chunk_dicts]
    else:
        print("\nSegmentando el corpus por párrafos (Fallback)...")
        chunks = [c.strip() for c in text_corpus.split("\n\n") if c.strip()]
        
    print(f"Total de fragmentos obtenidos: {len(chunks)}")
    for i, chunk in enumerate(chunks, start=1):
        print(f"  Fragmento {i}: '{chunk[:60]}...' ({len(chunk)} caracteres)")

    # 2. Inicialización del Extractor y del Almacén del Grafo
    # Nota: Si dispones de una clave API de Gemini en tu entorno (GEMINI_API_KEY),
    # el extractor la utilizará para invocar el modelo y generar un grafo real.
    # En caso contrario, se ejecutará en modo local-mock de forma automática.
    extractor = KnowledgeGraphExtractor()
    store = KnowledgeGraphStore()

    # 3. Procesamiento y Extracción por fragmento
    print("\nProcesando y extrayendo relaciones por cada fragmento...")
    for idx, chunk in enumerate(chunks, start=1):
        print(f"  Extrayendo grafo de fragmento {idx}/{len(chunks)}...")
        kg_extracted = extractor.extract(chunk)
        
        # Consolidamos las entidades y relaciones del fragmento en el almacén global
        # Aquí es donde ocurre la resolución de duplicados y fusión de metadatos de nodos
        store.add_graph(kg_extracted)

    # 4. Mostrar resumen del grafo consolidado
    graph_data = store.to_dict()
    print("\n" + "="*50)
    print(" Grafo de Conocimiento Consolidado ")
    print("="*50)
    print(f"Total Entidades Únicas: {len(graph_data['entities'])}")
    for ent in graph_data["entities"]:
        print(f"  • [{ent['type']}] {ent['name']}: {ent['description'][:70]}...")
        
    print(f"\nTotal Relaciones Consolidadas: {len(graph_data['relations'])}")
    for rel in graph_data["relations"]:
        print(f"  • {rel['source']} ──({rel['type']})──> {rel['target']} | {rel['description']}")

    # 5. Generar exportación para Base de Datos de Grafos (Neo4j Cypher)
    print("\n" + "="*50)
    print(" Generación de sentencias Neo4j Cypher (Muestra) ")
    print("="*50)
    cypher_script = store.to_neo4j_cypher()
    # Mostramos solo las primeras 10 líneas para revisión
    lines = cypher_script.split("\n")
    for line in lines[:12]:
        print(line)
    if len(lines) > 12:
        print(f"... y {len(lines) - 12} líneas más de consultas Cypher MERGE.")

    # 6. Renderizar y persistir visualización interactiva
    output_html = "graph_output.html"
    print(f"\nGenerando visualización interactiva en '{output_html}'...")
    visualizer = GraphVisualizer(store)
    visualizer.save_visualization(output_html)
    
    print("\n==================================================")
    print(" Demostración finalizada exitosamente.            ")
    print(f" Abre el archivo '{output_html}' en tu navegador   ")
    print(" para explorar el grafo de conocimiento.          ")
    print("==================================================")


if __name__ == "__main__":
    main()

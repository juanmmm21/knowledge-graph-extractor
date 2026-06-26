# Knowledge Graph Extractor

Pipeline para extraer grafos de conocimiento estructurados (Knowledge Graphs) a partir de texto no estructurado utilizando Modelos de Lenguaje (LLMs) y tecnicas de resolucion de entidades. Este subproyecto permite identificar conceptos clave (nodos) y sus interconexiones (relaciones) para alimentar arquitecturas avanzadas de recuperacion de informacion como GraphRAG.

## Arquitectura y Fundamentos Tecnicos

El procesamiento del pipeline sigue cuatro etapas principales:

### 1. Extraccion Estructurada con Pydantic
El extractor define un esquema estricto utilizando Pydantic para validar y estructurar las respuestas JSON provenientes del LLM. Los modelos definidos son:

```python
class Entity(BaseModel):
    name: str = Field(..., description="Nombre unico de la entidad (normalizado)")
    type: str = Field(..., description="Categoria (PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT)")
    description: str = Field(..., description="Resumen descriptivo del contexto o rol")

class Relation(BaseModel):
    source: str = Field(..., description="Nombre de la entidad origen")
    target: str = Field(..., description="Nombre de la entidad destino")
    type: str = Field(..., description="Verbo o relacion logica en minusculas (ej. trabaja_en)")
    description: str = Field(..., description="Detalle contextual de la relacion")

class KnowledgeGraph(BaseModel):
    entities: List[Entity]
    relations: List[Relation]
```

### 2. Resolucion de Entidades (Entity Resolution)
La informacion del texto libre suele presentar redundancias (ej. "Albert Einstein", "Einstein" o "einstein"). La clase `KnowledgeGraphStore` procesa cada entidad nueva y aplica tecnicas deterministicas para unificar nodos:
*   **Normalizacion de Nombres:** Se limpian espacios marginales y se evalua en minusculas para comparacion de claves de diccionario.
*   **Fusion Semantica (Merging):**
    *   Se preserva el nombre con mejor capitalizacion (la cadena mas larga).
    *   Se promueven categorias genericas a especificas (por ejemplo, si una entidad previa `CONCEPT` coincide con una nueva declarada `PERSON`).
    *   Se realiza una actualizacion incremental y sin duplicados de las descripciones historicas.

### 3. Exportacion Segura a Bases de Datos (Cypher)
Para persistir el grafo en Neo4j, se generan consultas Cypher escapando comillas simples y caracteres de escape de forma segura mediante comandos `MERGE`:

```cypher
MERGE (s:Entity {name: 'Albert Einstein'})
ON CREATE SET s.type = 'PERSON', s.description = 'Fisico aleman creador de la relatividad.'
ON MATCH SET s.description = s.description + ' ' + 'Fisico aleman creador de la relatividad.'

MERGE (t:Entity {name: 'Relatividad General'})
ON CREATE SET t.type = 'CONCEPT', t.description = 'Teoria geometrica de la gravitacion.'
ON MATCH SET t.description = t.description + ' ' + 'Teoria geometrica de la gravitacion.'

MERGE (s)-[r:desarrollo]->(t)
ON CREATE SET r.description = 'Formulo las ecuaciones de campo en 1915.'
```

### 4. Visualizacion Dinamica en D3.js
El modulo visualizador exporta un archivo HTML auto-contenido que carga D3.js desde un CDN y renderiza el grafo mediante un grafo dirigido con simulacion de fuerzas fisicas:
*   **Fuerza de Carga (`forceManyBody`):** Controla la repulsion entre nodos para evitar solapamientos ($F_{\text{rep}} \propto -1/d^2$).
*   **Fuerza de Enlace (`forceLink`):** Mantiene unidos los nodos conectados segun la distancia del enlace.
*   **Fuerza de Colision (`forceCollide`):** Define un radio fisico para cada circulo de nodo en la pantalla para mayor claridad visual.
*   **Fuerza de Centrado (`forceCenter`):** Mantiene la masa del grafo en el centro del viewport del canvas SVG.

## Requisitos de Instalacion

*   Python 3.10 o superior
*   Pydantic
*   Google-Genai (opcional, para extraccion con Gemini)
*   Jinja2 (para renderizar la plantilla HTML)

Para instalar los requisitos, ejecute:
```bash
pip install -r requirements.txt
```

## Guia de Ejecucion y Verificacion

### 1. Ejecutar Pruebas Unitarias
Comprueba la fusion de metadatos redundantes, integridad de escapes de Cypher y resiliencia del parser:
```bash
python3 -m unittest test_extractor.py
```

### 2. Ejecutar Demostración
```bash
python3 example.py
```
El script utilizara el segmentador `SemanticChunker` para trocear un corpus historico, procesara los fragmentos extrayendo subgrafos locales, unificara las entidades resolviendo duplicaciones, imprimira las sentencias Cypher en terminal y escribira el visualizador en `graph_output.html`.

## Conectividad en el Ecosistema ai-core-infra

El modulo `knowledge-graph-extractor` es crucial para arquitecturas GraphRAG:
*   Consume a [semantic-chunking-engine](https://github.com/juanmmm21/semantic-chunking-engine) para fragmentar la entrada de forma logica.
*   En la aplicacion final [nexus-second-brain](https://github.com/juanmmm21/nexus-second-brain), este motor procesa las notas del usuario en tiempo real para mantener actualizado su mapa mental de conceptos en la interfaz web de Obsidian-style.

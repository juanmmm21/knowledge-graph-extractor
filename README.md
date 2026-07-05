# Knowledge Graph Extractor

Pipeline for extracting structured knowledge graphs from unstructured text using Language Models (LLMs) and entity resolution techniques. This subproject identifies key concepts (nodes) and their interconnections (relations) to feed advanced information retrieval architectures such as GraphRAG.

## Architecture and Technical Foundations

The pipeline processing follows four main stages:

### 1. Structured Extraction with Pydantic
The extractor defines a strict schema using Pydantic to validate and structure the JSON responses coming from the LLM. The defined models are:

```python
class Entity(BaseModel):
    name: str = Field(..., description="Unique name of the entity (normalized)")
    type: str = Field(..., description="Category (PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT)")
    description: str = Field(..., description="Descriptive summary of the context or role")

class Relation(BaseModel):
    source: str = Field(..., description="Name of the source entity")
    target: str = Field(..., description="Name of the target entity")
    type: str = Field(..., description="Verb or logical relation in lowercase (e.g. works_at)")
    description: str = Field(..., description="Contextual detail of the relation")

class KnowledgeGraph(BaseModel):
    entities: List[Entity]
    relations: List[Relation]
```

### 2. Entity Resolution
Free-text information often presents redundancies (e.g. "Albert Einstein", "Einstein" or "einstein"). The `KnowledgeGraphStore` class processes each new entity and applies deterministic techniques to unify nodes:
*   **Name Normalization:** Leading/trailing spaces are trimmed and the name is evaluated in lowercase for dictionary key comparison.
*   **Semantic Merging:**
    *   The name with the best capitalization (the longest string) is preserved.
    *   Generic categories are promoted to specific ones (for example, if a previous `CONCEPT` entity matches a newly declared `PERSON`).
    *   An incremental, duplicate-free update of historical descriptions is performed.

### 3. Safe Export to Databases (Cypher)
To persist the graph in Neo4j, Cypher queries are generated, safely escaping single quotes and escape characters via `MERGE` commands:

```cypher
MERGE (s:Entity {name: 'Albert Einstein'})
ON CREATE SET s.type = 'PERSON', s.description = 'German physicist who created relativity.'
ON MATCH SET s.description = s.description + ' ' + 'German physicist who created relativity.'

MERGE (t:Entity {name: 'General Relativity'})
ON CREATE SET t.type = 'CONCEPT', t.description = 'Geometric theory of gravitation.'
ON MATCH SET t.description = t.description + ' ' + 'Geometric theory of gravitation.'

MERGE (s)-[r:developed]->(t)
ON CREATE SET r.description = 'Formulated the field equations in 1915.'
```

### 4. Dynamic Visualization in D3.js
The visualizer module exports a self-contained HTML file that loads D3.js from a CDN and renders the graph as a directed graph with physics-based force simulation:
*   **Charge Force (`forceManyBody`):** Controls repulsion between nodes to avoid overlap ($F_{\text{rep}} \propto -1/d^2$).
*   **Link Force (`forceLink`):** Keeps connected nodes together according to link distance.
*   **Collision Force (`forceCollide`):** Defines a physical radius for each node circle on screen for greater visual clarity.
*   **Centering Force (`forceCenter`):** Keeps the graph's mass centered in the SVG canvas viewport.

## Installation Requirements

*   Python 3.10 or higher
*   Pydantic
*   Google-Genai (optional, for extraction with Gemini)
*   Jinja2 (to render the HTML template)

To install the requirements, run:
```bash
pip install -r requirements.txt
```

## Execution and Verification Guide

### 1. Run Unit Tests
Checks the merging of redundant metadata, Cypher escape integrity, and parser resilience:
```bash
python3 -m unittest test_extractor.py
```

### 2. Run Demo
```bash
python3 example.py
```
The script will use the `SemanticChunker` segmenter to chunk a historical corpus, process the fragments extracting local subgraphs, unify entities resolving duplicates, print the Cypher statements to the terminal, and write the visualizer to `graph_output.html`.

## Connectivity within the ai-core-infra Ecosystem

The `knowledge-graph-extractor` module is crucial for GraphRAG architectures:
*   It consumes [semantic-chunking-engine](https://github.com/juanmmm21/semantic-chunking-engine) to logically fragment the input.
*   In the final application [nexus-second-brain](https://github.com/juanmmm21/nexus-second-brain), this engine processes the user's notes in real time to keep their concept mind map up to date in the Obsidian-style web interface.

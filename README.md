# knowledge-graph-extractor

Pipeline para extraer grafos de conocimiento estructurados (Knowledge Graphs) a partir de texto no estructurado utilizando Modelos de Lenguaje (LLMs) y tecnicas de resolucion de entidades.

Este subproyecto permite identificar conceptos clave (nodos) y sus interconexiones (relaciones) para alimentar arquitecturas avanzadas de recuperacion de informacion como GraphRAG.

## Arquitectura y Fundamentos Tecnicos

El procesamiento del pipeline sigue cuatro etapas principales:

### 1. Extracción Estructurada con Pydantic
Para garantizar que las respuestas del LLM cumplan con la estructura tipada estricta, el extractor utiliza la funcionalidad de salida estructurada (JSON Schema nativo) a traves de Pydantic. Los esquemas definidos son:
*   **Entity:** Almacena `name`, `type` (PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT) y `description`.
*   **Relation:** Almacena `source`, `target` (que deben coincidir con nombres de entidades), `type` y `description`.
*   **KnowledgeGraph:** Estructura que engloba una lista de entidades y de relaciones.

### 2. Resolución de Entidades (Entity Resolution)
La informacion del texto libre suele presentar redundancias (ej. "Albert Einstein", "Einstein" o "einstein"). La clase `KnowledgeGraphStore` procesa cada entidad nueva y:
*   Normaliza el nombre a minusculas y sin espacios marginales para evaluar su unicidad.
*   En caso de coincidencia (nodo duplicado), conserva el nombre con mejor capitalizacion (la cadena mas larga).
*   Promueve tipos genericos a especificos (ej. si era `CONCEPT` y se descubre como `PERSON`).
*   Concatena las descripciones extraidas de forma incremental sin introducir duplicaciones textuales.

### 3. Exportación a Bases de Datos (Neo4j Cypher)
Para transferir el grafo de memoria a una base de datos de grafos de produccion, el pipeline genera sentencias Cypher utilizando comandos seguros `MERGE`. Esto permite actualizar las descripciones de los nodos y relaciones existentes o crearlos si no existen, escapando caracteres conflictivos como comillas simples.

### 4. Visualización Dinámica HTML y D3.js
El modulo genera una interfaz web interactiva auto-contenida en un archivo HTML de diseño premium en modo oscuro. D3.js gestiona la fisica de fuerzas de los nodos, permitiendo arrastrar elementos, aplicar zoom, mostrar tooltips al posar el cursor sobre nodos o aristas, e iluminar las conexiones directas del nodo seleccionado.

## Conexión con el Ecosistema

Este proyecto interactua con otros modulos de la infraestructura `ai-core-infra`:
*   **semantic-chunking-engine:** En el script de demostracion, el extractor importa el chunker semantico hermano para procesar corpus extensos fragmentandolos tematicamente en lugar de realizar cortes arbitrarios por parrafos. Esto optimiza la ventana de contexto del LLM y mejora la precision de la extraccion.

## Estructura del Proyecto

*   **extractor.py:** Define los modelos Pydantic y el cliente extractor. Soporta integracion con Gemini y fallback determinista offline.
*   **graph.py:** Define la logica del grafo, resolucion de entidades, guardado JSON y exportacion Cypher.
*   **visualizer.py:** Generador de la plantilla HTML interactiva con D3.js.
*   **test_extractor.py:** Suite de pruebas unitarias.
*   **example.py:** Demostracion completa interconectando la fragmentacion semantica con la extraccion y visualizacion.

## Instalacion y Requisitos

1. Crea e inicia un entorno virtual dentro de la carpeta del proyecto:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Instrucciones de Uso

### Ejecutar Pruebas Unitarias
Para validar el comportamiento offline, fusion de nodos, relaciones y generacion Cypher:
```bash
python -m unittest test_extractor.py
```

### Ejecutar Demostración
Para procesar un texto cientifico sobre historia de la ciencia y generar la visualizacion interactiva:
```bash
python example.py
```
El script generara el archivo `graph_output.html` en la raiz del proyecto. Puedes abrirlo haciendo doble clic sobre el desde tu navegador para interactuar visualmente con el grafo de conocimiento extraido.

import os
import json
import logging
from typing import Dict, Any
from graph import KnowledgeGraphStore

logger = logging.getLogger(__name__)

class GraphVisualizer:
    """
    Exportador y renderizador para visualizaciones interactivas de Grafos de Conocimiento.
    
    Genera un archivo HTML auto-contenido que lee D3.js desde un CDN y renderiza
    un grafo de nodos y enlaces interactivo con soporte para zoom, arrastre y tooltips.
    """
    
    def __init__(self, store: KnowledgeGraphStore) -> None:
        self.store = store

    def _generate_html_content(self) -> str:
        """
        Produce el codigo HTML/CSS/JS completo necesario para renderizar el grafo.
        """
        # Convertimos los datos del almacen a JSON apto para D3.js
        graph_dict = self.store.to_dict()
        
        # En D3.js force simulation, los links requieren 'source' y 'target' que correspondan
        # con los IDs de los nodos. En nuestro caso, los IDs de los nodos seran los nombres de las entidades.
        nodes_data = []
        for ent in self.store.entities.values():
            nodes_data.append({
                "id": ent.name,
                "type": ent.type,
                "description": ent.description
            })
            
        links_data = []
        for rel in self.store.relations:
            links_data.append({
                "source": rel.source,
                "target": rel.target,
                "type": rel.type,
                "description": rel.description
            })
            
        graph_json = json.dumps({"nodes": nodes_data, "links": links_data}, indent=2, ensure_ascii=False)
        
        # Codigo HTML embebido
        html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visualización de Grafo de Conocimiento</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
            background-color: #0b0e14;
            color: #f8f8f2;
            font-family: 'Outfit', sans-serif;
            overflow: hidden;
        }}
        #graph-container {{
            width: 100vw;
            height: 100vh;
            display: block;
        }}
        .link {{
            stroke: #44475a;
            stroke-opacity: 0.6;
            stroke-width: 2px;
            transition: stroke 0.25s ease, stroke-opacity 0.25s ease, stroke-width 0.25s ease;
        }}
        .link-highlight {{
            stroke: #bd93f9 !important;
            stroke-opacity: 1.0 !important;
            stroke-width: 3.5px !important;
        }}
        .node {{
            stroke: #1e222b;
            stroke-width: 2px;
            cursor: pointer;
            transition: stroke 0.25s ease, stroke-width 0.25s ease;
        }}
        .node:hover {{
            stroke: #ffffff;
            stroke-width: 3px;
        }}
        .node-label {{
            fill: #e2e8f0;
            font-size: 11px;
            font-weight: 400;
            pointer-events: none;
            text-anchor: middle;
            text-shadow: 0px 1px 4px rgba(0, 0, 0, 0.95), 0px 1px 2px rgba(0, 0, 0, 0.95);
        }}
        .tooltip {{
            position: absolute;
            background-color: rgba(15, 23, 42, 0.95);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s ease;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
            max-width: 300px;
            font-size: 13px;
            line-height: 1.5;
            z-index: 100;
        }}
        .tooltip-title {{
            font-weight: 600;
            font-size: 14px;
            color: #ffffff;
            margin-bottom: 4px;
        }}
        .tooltip-type {{
            font-size: 10px;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
            color: #38bdf8;
            margin-bottom: 8px;
        }}
        .tooltip-desc {{
            color: #94a3b8;
        }}
        .header {{
            position: absolute;
            top: 24px;
            left: 24px;
            pointer-events: none;
            z-index: 10;
        }}
        .header h1 {{
            margin: 0 0 4px 0;
            font-size: 22px;
            font-weight: 600;
            letter-spacing: -0.025em;
            color: #ffffff;
        }}
        .header p {{
            margin: 0;
            font-size: 13px;
            color: #64748b;
        }}
        .legend {{
            position: absolute;
            bottom: 24px;
            left: 24px;
            background-color: rgba(15, 23, 42, 0.85);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 14px;
            font-size: 12px;
            z-index: 10;
            backdrop-filter: blur(8px);
        }}
        .legend-title {{
            font-weight: 600;
            margin-bottom: 8px;
            color: #f1f5f9;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 6px;
        }}
        .legend-color {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Knowledge Graph</h1>
        <p>Grafo interactivo de entidades y relaciones extraídas de texto</p>
    </div>
    
    <div class="legend">
        <div class="legend-title">Categorías</div>
        <div class="legend-item"><div class="legend-color" style="background-color: #ff79c6;"></div>PERSON</div>
        <div class="legend-item"><div class="legend-color" style="background-color: #8be9fd;"></div>ORGANIZATION</div>
        <div class="legend-item"><div class="legend-color" style="background-color: #50fa7b;"></div>LOCATION</div>
        <div class="legend-item"><div class="legend-color" style="background-color: #bd93f9;"></div>CONCEPT</div>
        <div class="legend-item"><div class="legend-color" style="background-color: #ffb86c;"></div>EVENT</div>
        <div class="legend-item"><div class="legend-color" style="background-color: #94a3b8;"></div>OTHER</div>
    </div>
    
    <div class="tooltip" id="tooltip"></div>
    <svg id="graph-container"></svg>

    <script>
        // Datos inyectados por Python
        const graph = {graph_json};

        // Paleta de colores Premium (Dracula-inspired) para los tipos de entidad
        const colorScale = (type) => {{
            const colors = {{
                "PERSON": "#ff79c6",
                "ORGANIZATION": "#8be9fd",
                "LOCATION": "#50fa7b",
                "CONCEPT": "#bd93f9",
                "EVENT": "#ffb86c"
            }};
            return colors[type.toUpperCase()] || "#94a3b8";
        }};

        const svg = d3.select("#graph-container");
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        // Habilitamos zoom y arrastre sobre el fondo
        const g = svg.append("g");
        
        const zoom = d3.zoom()
            .scaleExtent([0.2, 4])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }});
            
        svg.call(zoom);

        // Simulacion fisica de fuerzas
        const simulation = d3.forceSimulation(graph.nodes)
            .force("link", d3.forceLink(graph.links).id(d => d.id).distance(120))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(40));

        // Renderizado de las aristas (relaciones)
        const link = g.append("g")
            .selectAll("line")
            .data(graph.links)
            .enter().append("line")
            .attr("class", "link")
            .on("mouseover", showLinkTooltip)
            .on("mouseout", hideTooltip);

        // Renderizado de los nodos (entidades)
        const node = g.append("g")
            .selectAll("circle")
            .data(graph.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", d => d.type === "CONCEPT" ? 14 : 11)
            .attr("fill", d => colorScale(d.type))
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended))
            .on("mouseover", showNodeTooltip)
            .on("mouseout", hideTooltip);

        // Etiquetas de texto sobre los nodos
        const label = g.append("g")
            .selectAll("text")
            .data(graph.nodes)
            .enter().append("text")
            .attr("class", "node-label")
            .attr("dy", d => d.type === "CONCEPT" ? 22 : 18)
            .text(d => d.id);

        // Actualizaciones de posiciones en cada tick de la simulacion fisica
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);

            label
                .attr("x", d => d.x)
                .attr("y", d => d.y);
        }});

        // Funciones de Tooltips
        const tooltip = d3.select("#tooltip");

        function showNodeTooltip(event, d) {{
            tooltip
                .style("opacity", 1)
                .html(`
                    <div class="tooltip-title">${{d.id}}</div>
                    <div class="tooltip-type">${{d.type}}</div>
                    <div class="tooltip-desc">${{d.description}}</div>
                `)
                .style("left", (event.pageX + 15) + "px")
                .style("top", (event.pageY - 15) + "px");
                
            // Resaltamos enlaces conectados
            link.classed("link-highlight", l => l.source.id === d.id || l.target.id === d.id);
        }}

        function showLinkTooltip(event, d) {{
            tooltip
                .style("opacity", 1)
                .html(`
                    <div class="tooltip-title" style="color: #bd93f9">${{d.type}}</div>
                    <div class="tooltip-type" style="color: #64748b">${{d.source.id}} → ${{d.target.id}}</div>
                    <div class="tooltip-desc">${{d.description}}</div>
                `)
                .style("left", (event.pageX + 15) + "px")
                .style("top", (event.pageY - 15) + "px");
                
            // Resaltamos el enlace hovered
            d3.select(event.currentTarget).classed("link-highlight", true);
        }}

        function hideTooltip(event, d) {{
            tooltip.style("opacity", 0);
            link.classed("link-highlight", false);
        }}

        // Funciones de Arrastre (Drag and Drop)
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}

        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
            tooltip
                .style("left", (event.sourceEvent.pageX + 15) + "px")
                .style("top", (event.sourceEvent.pageY - 15) + "px");
        }}

        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}

        // Redimensionar responsivamente
        window.addEventListener("resize", () => {{
            const w = window.innerWidth;
            const h = window.innerHeight;
            svg.attr("width", w).attr("height", h);
            simulation.force("center", d3.forceCenter(w / 2, h / 2)).restart();
        }});
    </script>
</body>
</html>
"""
        return html_template

    def save_visualization(self, filepath: str) -> None:
        """
        Genera y escribe la visualizacion HTML interactiva en la ruta provista.
        """
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        html_content = self._generate_html_content()
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Visualizacion interactiva HTML generada exitosamente en {filepath}")
        except Exception as e:
            logger.error(f"Error al escribir visualizacion HTML en {filepath}: {str(e)}")
            raise

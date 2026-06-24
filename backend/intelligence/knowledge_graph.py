"""
MJ Intelligence: Knowledge Graph
In-memory graph that links entities and concepts extracted from KB documents.
Supports: entity extraction, relationship mapping, graph queries, path finding.
No external dependencies — uses regex-based NER and adjacency lists.
"""

import re
import json
import logging
import time
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("mj.knowledge_graph")

GRAPH_FILE = Path(__file__).parent.parent / "knowledge_base" / "graph.json"


class KnowledgeGraph:
    """
    In-memory knowledge graph built from KB documents.
    Nodes = entities (people, concepts, tools, topics).
    Edges = relationships (mentions, relates_to, part_of, uses).
    """

    def __init__(self):
        self.nodes: Dict[str, dict] = {}  # id -> {label, type, sources, properties}
        self.edges: List[dict] = []  # {from, to, relation, weight, source}
        self._adjacency: Dict[str, List[str]] = defaultdict(list)
        self._load()

    # ========================
    # ENTITY EXTRACTION
    # ========================

    # Patterns for extracting entities from text
    ENTITY_PATTERNS = {
        "technology": re.compile(
            r"\b(Python|JavaScript|TypeScript|React|Vue|Angular|Node\.?js|FastAPI|Django|Flask|"
            r"Docker|Kubernetes|AWS|Azure|GCP|MongoDB|PostgreSQL|MySQL|Redis|"
            r"TensorFlow|PyTorch|LLM|GPT|Ollama|Groq|API|REST|GraphQL|"
            r"HTML|CSS|Git|Linux|Windows|macOS|Nginx|Apache)\b", re.IGNORECASE
        ),
        "concept": re.compile(
            r"\b(machine learning|deep learning|neural network|natural language processing|"
            r"artificial intelligence|computer vision|reinforcement learning|"
            r"microservices|serverless|devops|CI/CD|agile|scrum|"
            r"encryption|authentication|authorization|OAuth|JWT|"
            r"database|cache|queue|API gateway|load balancer|"
            r"RAG|vector database|embedding|tokenization|fine[- ]tuning)\b", re.IGNORECASE
        ),
        "person": re.compile(
            r"\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
        ),
        "organization": re.compile(
            r"\b(Google|Microsoft|Amazon|Apple|Meta|OpenAI|Anthropic|"
            r"Netflix|Uber|Spotify|GitHub|StackOverflow|"
            r"NASA|WHO|UN|IEEE|ACM)\b", re.IGNORECASE
        ),
    }

    def extract_entities(self, text: str, source: str = "") -> List[dict]:
        """Extract entities from text using regex patterns."""
        entities = []
        seen = set()

        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = pattern.findall(text)
            for match in matches:
                label = match.strip()
                if len(label) < 2 or label.lower() in seen:
                    continue
                seen.add(label.lower())
                entities.append({
                    "label": label,
                    "type": entity_type,
                    "source": source,
                })

        return entities

    def extract_relationships(self, text: str, entities: List[dict]) -> List[dict]:
        """Extract relationships between entities found in the same text chunk."""
        relationships = []
        entity_labels = [e["label"] for e in entities]

        # Co-occurrence: entities in the same sentence are related
        sentences = re.split(r'[.!?\n]', text)
        for sent in sentences:
            sent_lower = sent.lower()
            in_sentence = [e for e in entity_labels if e.lower() in sent_lower]
            for i, e1 in enumerate(in_sentence):
                for e2 in in_sentence[i + 1:]:
                    # Determine relation type from context
                    relation = "relates_to"
                    if re.search(r"(?:uses?|using|with|via)\s", sent_lower):
                        relation = "uses"
                    elif re.search(r"(?:part of|belongs? to|within|inside)\s", sent_lower):
                        relation = "part_of"
                    elif re.search(r"(?:is a|is an|type of|kind of)\s", sent_lower):
                        relation = "is_a"
                    elif re.search(r"(?:built|made|created|developed)\s", sent_lower):
                        relation = "created_by"

                    relationships.append({
                        "from": e1.lower(),
                        "to": e2.lower(),
                        "relation": relation,
                    })

        return relationships

    # ========================
    # GRAPH OPERATIONS
    # ========================

    def add_node(self, label: str, entity_type: str = "concept",
                 source: str = "", properties: dict = None) -> str:
        """Add a node to the graph. Returns node ID."""
        node_id = label.lower().replace(" ", "_")
        if node_id in self.nodes:
            # Update existing — add source
            if source and source not in self.nodes[node_id]["sources"]:
                self.nodes[node_id]["sources"].append(source)
            if properties:
                self.nodes[node_id]["properties"].update(properties)
            return node_id

        self.nodes[node_id] = {
            "id": node_id,
            "label": label,
            "type": entity_type,
            "sources": [source] if source else [],
            "properties": properties or {},
            "created": time.time(),
        }
        return node_id

    def add_edge(self, from_label: str, to_label: str,
                 relation: str = "relates_to", weight: float = 1.0, source: str = ""):
        """Add an edge between two nodes."""
        from_id = from_label.lower().replace(" ", "_")
        to_id = to_label.lower().replace(" ", "_")

        # Auto-create nodes if they don't exist
        if from_id not in self.nodes:
            self.add_node(from_label, source=source)
        if to_id not in self.nodes:
            self.add_node(to_label, source=source)

        # Check for duplicate edge
        for edge in self.edges:
            if edge["from"] == from_id and edge["to"] == to_id and edge["relation"] == relation:
                edge["weight"] += 0.5  # Strengthen existing edge
                return

        self.edges.append({
            "from": from_id,
            "to": to_id,
            "relation": relation,
            "weight": weight,
            "source": source,
        })
        self._adjacency[from_id].append(to_id)
        self._adjacency[to_id].append(from_id)

    def build_from_text(self, text: str, source: str = "") -> dict:
        """Build graph nodes and edges from a text chunk."""
        entities = self.extract_entities(text, source)
        relationships = self.extract_relationships(text, entities)

        nodes_added = 0
        edges_added = 0

        for entity in entities:
            self.add_node(entity["label"], entity["type"], source)
            nodes_added += 1

        for rel in relationships:
            self.add_edge(rel["from"], rel["to"], rel["relation"], source=source)
            edges_added += 1

        self._save()
        return {"nodes_added": nodes_added, "edges_added": edges_added, "source": source}

    def build_from_kb(self) -> dict:
        """Build graph from all knowledge base documents."""
        from intelligence.knowledge_base import _load_index, CHUNKS_DIR
        index = _load_index()
        total_nodes = 0
        total_edges = 0

        for doc in index.get("documents", []):
            chunk_file = CHUNKS_DIR / f"{doc['id']}.json"
            if chunk_file.exists():
                chunks = json.loads(chunk_file.read_text(encoding="utf-8"))
                for chunk in chunks:
                    result = self.build_from_text(chunk["text"], doc["filename"])
                    total_nodes += result["nodes_added"]
                    total_edges += result["edges_added"]

        self._save()
        return {
            "documents_processed": len(index.get("documents", [])),
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "new_nodes": total_nodes,
            "new_edges": total_edges,
        }

    # ========================
    # QUERIES
    # ========================

    def get_node(self, label: str) -> Optional[dict]:
        """Get a node by label."""
        node_id = label.lower().replace(" ", "_")
        node = self.nodes.get(node_id)
        if not node:
            return None
        # Include connections
        connections = self.get_connections(label)
        return {**node, "connections": connections}

    def get_connections(self, label: str) -> List[dict]:
        """Get all nodes connected to a given node."""
        node_id = label.lower().replace(" ", "_")
        connections = []
        for edge in self.edges:
            if edge["from"] == node_id:
                target = self.nodes.get(edge["to"], {})
                connections.append({
                    "node": edge["to"],
                    "label": target.get("label", edge["to"]),
                    "type": target.get("type", "unknown"),
                    "relation": edge["relation"],
                    "direction": "outgoing",
                    "weight": edge["weight"],
                })
            elif edge["to"] == node_id:
                target = self.nodes.get(edge["from"], {})
                connections.append({
                    "node": edge["from"],
                    "label": target.get("label", edge["from"]),
                    "type": target.get("type", "unknown"),
                    "relation": edge["relation"],
                    "direction": "incoming",
                    "weight": edge["weight"],
                })
        connections.sort(key=lambda x: -x["weight"])
        return connections

    def find_path(self, from_label: str, to_label: str, max_depth: int = 4) -> Optional[List[str]]:
        """Find shortest path between two nodes using BFS."""
        from_id = from_label.lower().replace(" ", "_")
        to_id = to_label.lower().replace(" ", "_")

        if from_id not in self.nodes or to_id not in self.nodes:
            return None

        visited: Set[str] = set()
        queue: List[Tuple[str, List[str]]] = [(from_id, [from_id])]

        while queue:
            current, path = queue.pop(0)
            if current == to_id:
                return [self.nodes.get(n, {}).get("label", n) for n in path]
            if len(path) > max_depth:
                continue
            if current in visited:
                continue
            visited.add(current)
            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return None

    def search_nodes(self, query: str, limit: int = 10) -> List[dict]:
        """Search nodes by label (fuzzy match)."""
        query_lower = query.lower()
        results = []
        for node_id, node in self.nodes.items():
            label_lower = node["label"].lower()
            if query_lower in label_lower or label_lower in query_lower:
                results.append({
                    **node,
                    "connections_count": len(self._adjacency.get(node_id, [])),
                })
        results.sort(key=lambda x: -x["connections_count"])
        return results[:limit]

    def get_stats(self) -> dict:
        """Get graph statistics."""
        type_counts = defaultdict(int)
        for node in self.nodes.values():
            type_counts[node["type"]] += 1

        relation_counts = defaultdict(int)
        for edge in self.edges:
            relation_counts[edge["relation"]] += 1

        # Top connected nodes
        connection_counts = {n: len(neighbors) for n, neighbors in self._adjacency.items()}
        top_nodes = sorted(connection_counts.items(), key=lambda x: -x[1])[:10]

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(type_counts),
            "relation_types": dict(relation_counts),
            "top_connected": [
                {"node": self.nodes.get(n, {}).get("label", n), "connections": c}
                for n, c in top_nodes
            ],
        }

    def get_all(self, limit: int = 200) -> dict:
        """Get full graph data for visualization."""
        nodes = list(self.nodes.values())[:limit]
        node_ids = {n["id"] for n in nodes}
        edges = [e for e in self.edges if e["from"] in node_ids and e["to"] in node_ids]
        return {"nodes": nodes, "edges": edges}

    def clear(self):
        """Clear the entire graph."""
        self.nodes.clear()
        self.edges.clear()
        self._adjacency.clear()
        self._save()

    # ========================
    # PERSISTENCE
    # ========================

    def _load(self):
        if GRAPH_FILE.exists():
            try:
                data = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", [])
                # Rebuild adjacency
                for edge in self.edges:
                    self._adjacency[edge["from"]].append(edge["to"])
                    self._adjacency[edge["to"]].append(edge["from"])
            except Exception as e:
                logger.warning(f"Failed to load knowledge graph: {e}")

    def _save(self):
        try:
            GRAPH_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"nodes": self.nodes, "edges": self.edges, "saved": time.time()}
            GRAPH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save knowledge graph: {e}")


# Singleton
knowledge_graph = KnowledgeGraph()

"""
Retriever Component for CGM

Retrieves relevant code subgraphs based on anchor nodes
"""

from typing import Any, Dict, List, Set, Tuple

import networkx as nx
from fuzzywuzzy import fuzz
from loguru import logger

from ..models import RetrieverRequest, RetrieverResponse


class RetrieverComponent:
    """
    Retriever component that identifies anchor nodes and extracts
    relevant subgraphs from the repository code graph
    """

    def __init__(self):
        self.similarity_threshold = 70  # Fuzzy matching threshold

    def locate_anchor_nodes(
        self,
        entities: List[str],
        keywords: List[str],
        queries: List[str],
        graph: nx.Graph,
    ) -> List[str]:
        """
        Locate anchor nodes in the code graph based on entities, keywords, and queries
        """
        anchor_nodes = set()

        # Direct entity matching
        for entity in entities:
            matching_nodes = self._find_matching_nodes(entity, graph)
            anchor_nodes.update(matching_nodes)

        # Keyword-based matching
        for keyword in keywords:
            matching_nodes = self._find_nodes_by_keyword(keyword, graph)
            anchor_nodes.update(matching_nodes)

        # Query-based matching (if available)
        if queries:
            for query in queries:
                matching_nodes = self._find_nodes_by_query(query, graph)
                anchor_nodes.update(matching_nodes)

        return list(anchor_nodes)

    def _find_matching_nodes(self, entity: str, graph: nx.Graph) -> List[str]:
        """Find nodes that match the given entity"""
        matching_nodes = []

        for node in graph.nodes():
            node_data = graph.nodes[node]

            # Direct name matching
            if entity in node:
                matching_nodes.append(node)
                continue

            # Fuzzy matching with node attributes
            node_name = node_data.get("name", node)
            if (
                fuzz.ratio(entity.lower(), node_name.lower())
                > self.similarity_threshold
            ):
                matching_nodes.append(node)
                continue

            # Check file path matching
            file_path = node_data.get("file_path", "")
            if entity in file_path:
                matching_nodes.append(node)
                continue

            # Check class/function name matching
            class_name = node_data.get("class_name", "")
            function_name = node_data.get("function_name", "")

            if (
                entity in class_name
                or entity in function_name
                or fuzz.ratio(entity.lower(), class_name.lower())
                > self.similarity_threshold
                or fuzz.ratio(entity.lower(), function_name.lower())
                > self.similarity_threshold
            ):
                matching_nodes.append(node)

        return matching_nodes

    def _find_nodes_by_keyword(self, keyword: str, graph: nx.Graph) -> List[str]:
        """Find nodes that contain the given keyword"""
        matching_nodes = []

        for node in graph.nodes():
            node_data = graph.nodes[node]

            # Check in node content/docstring
            content = node_data.get("content", "").lower()
            docstring = node_data.get("docstring", "").lower()

            if (
                keyword.lower() in content
                or keyword.lower() in docstring
                or keyword.lower() in node.lower()
            ):
                matching_nodes.append(node)

        return matching_nodes

    def _find_nodes_by_query(self, query: str, graph: nx.Graph) -> List[str]:
        """Find nodes based on natural language query"""
        matching_nodes = []
        query_lower = query.lower()

        # Extract key terms from query
        key_terms = self._extract_key_terms(query)

        for node in graph.nodes():
            node_data = graph.nodes[node]
            score = 0

            # Score based on key terms presence
            content = (
                node_data.get("content", "")
                + " "
                + node_data.get("docstring", "")
                + " "
                + node_data.get("name", "")
                + " "
                + node
            ).lower()

            for term in key_terms:
                if term in content:
                    score += 1

            # If enough terms match, consider it relevant
            if score >= len(key_terms) * 0.3:  # At least 30% of terms match
                matching_nodes.append(node)

        return matching_nodes

    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms from a natural language query"""
        # Simple keyword extraction - can be enhanced with NLP
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
        }

        words = query.lower().split()
        key_terms = [
            word.strip('.,!?;:"()[]{}')
            for word in words
            if word.lower() not in stop_words and len(word) > 2
        ]

        return key_terms

    def extract_subgraph(
        self,
        anchor_nodes: List[str],
        graph: nx.Graph,
        max_depth: int = 2,
        max_nodes: int = 100,
    ) -> Dict[str, Any]:
        """
        Extract a relevant subgraph around the anchor nodes
        """
        if not anchor_nodes:
            return {"nodes": [], "edges": [], "metadata": {}}

        subgraph_nodes = set(anchor_nodes)

        # Expand around anchor nodes
        for depth in range(max_depth):
            new_nodes = set()
            for node in list(subgraph_nodes):
                if node in graph:
                    # Add neighbors
                    neighbors = list(graph.neighbors(node))
                    new_nodes.update(neighbors)

            subgraph_nodes.update(new_nodes)

            # Limit subgraph size
            if len(subgraph_nodes) > max_nodes:
                # Keep the most connected nodes
                subgraph_nodes = self._select_top_nodes(
                    list(subgraph_nodes), graph, max_nodes
                )
                break

        # Create subgraph
        subgraph = graph.subgraph(subgraph_nodes)

        # Convert to serializable format
        nodes_data = []
        for node in subgraph.nodes():
            node_data = dict(subgraph.nodes[node])
            node_data["id"] = node
            nodes_data.append(node_data)

        edges_data = []
        for edge in subgraph.edges():
            edge_data = dict(subgraph.edges[edge])
            edge_data["source"] = edge[0]
            edge_data["target"] = edge[1]
            edges_data.append(edge_data)

        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "metadata": {
                "anchor_nodes": anchor_nodes,
                "total_nodes": len(nodes_data),
                "total_edges": len(edges_data),
                "max_depth": max_depth,
            },
        }

    def _select_top_nodes(
        self, nodes: List[str], graph: nx.Graph, max_nodes: int
    ) -> Set[str]:
        """Select top nodes based on centrality measures"""
        if len(nodes) <= max_nodes:
            return set(nodes)

        # Calculate centrality scores
        subgraph = graph.subgraph(nodes)
        centrality_scores = nx.degree_centrality(subgraph)

        # Sort by centrality and take top nodes
        sorted_nodes = sorted(
            centrality_scores.items(), key=lambda x: x[1], reverse=True
        )

        return set([node for node, _ in sorted_nodes[:max_nodes]])

    def get_relevant_files(self, subgraph: Dict[str, Any]) -> List[str]:
        """Extract list of relevant files from subgraph"""
        files = set()

        for node_data in subgraph.get("nodes", []):
            file_path = node_data.get("file_path")
            if file_path:
                files.add(file_path)

        return sorted(list(files))

    async def process(self, request: RetrieverRequest) -> RetrieverResponse:
        """Process a retriever request"""
        try:
            logger.info("Processing retriever request")

            # Convert repository graph to NetworkX graph
            graph = self._dict_to_networkx(request.repository_graph)

            # Locate anchor nodes
            anchor_nodes = self.locate_anchor_nodes(
                request.entities, request.keywords, request.queries or [], graph
            )

            logger.info(f"Found {len(anchor_nodes)} anchor nodes")

            # Extract subgraph
            subgraph = self.extract_subgraph(anchor_nodes, graph)

            # Get relevant files
            relevant_files = self.get_relevant_files(subgraph)

            return RetrieverResponse(
                anchor_nodes=anchor_nodes,
                subgraph=subgraph,
                relevant_files=relevant_files,
            )

        except Exception as e:
            logger.error(f"Error in retriever processing: {e}")
            raise

    def _dict_to_networkx(self, graph_dict: Dict[str, Any]) -> nx.Graph:
        """Convert dictionary representation to NetworkX graph"""
        graph = nx.Graph()

        # Add nodes
        for node_data in graph_dict.get("nodes", []):
            node_id = node_data.get("id")
            if node_id:
                graph.add_node(
                    node_id, **{k: v for k, v in node_data.items() if k != "id"}
                )

        # Add edges
        for edge_data in graph_dict.get("edges", []):
            source = edge_data.get("source")
            target = edge_data.get("target")
            if source and target:
                graph.add_edge(
                    source,
                    target,
                    **{
                        k: v
                        for k, v in edge_data.items()
                        if k not in ["source", "target"]
                    },
                )

        return graph

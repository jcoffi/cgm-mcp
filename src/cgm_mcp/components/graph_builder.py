"""
Graph Builder Component for CGM

Builds repository-level code graphs from source code
"""

import ast
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import networkx as nx
from loguru import logger


class GraphBuilder:
    """
    Graph builder that constructs repository-level code graphs
    from source code files
    """

    def __init__(self):
        self.supported_extensions = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".h"}

    async def build_graph(
        self, repository_name: str, repository_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a code graph for the repository"""
        try:
            logger.info(f"Building code graph for repository: {repository_name}")

            # Initialize graph
            graph = nx.DiGraph()

            # Get repository path from context or use default
            repo_path = self._get_repository_path(repository_name, repository_context)

            if not repo_path or not os.path.exists(repo_path):
                logger.warning(f"Repository path not found: {repo_path}")
                return self._create_empty_graph()

            # Analyze source files
            await self._analyze_repository(repo_path, graph)

            # Convert to serializable format
            return self._graph_to_dict(graph)

        except Exception as e:
            logger.error(f"Error building code graph: {e}")
            return self._create_empty_graph()

    def _get_repository_path(
        self, repository_name: str, repository_context: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Get the repository path from context or infer it"""
        if repository_context and "path" in repository_context:
            return repository_context["path"]

        # Try common locations
        possible_paths = [
            f"./{repository_name}",
            f"../{repository_name}",
            f"/tmp/{repository_name}",
            f"~/repositories/{repository_name}",
        ]

        for path in possible_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path

        return None

    async def _analyze_repository(self, repo_path: str, graph: nx.DiGraph):
        """Analyze all source files in the repository"""
        for root, dirs, files in os.walk(repo_path):
            # Skip common non-source directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in {"node_modules", "__pycache__", "build", "dist"}
            ]

            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)

                if self._should_analyze_file(file_path):
                    await self._analyze_file(file_path, relative_path, graph)

    def _should_analyze_file(self, file_path: str) -> bool:
        """Check if file should be analyzed"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    async def _analyze_file(
        self, file_path: str, relative_path: str, graph: nx.DiGraph
    ):
        """Analyze a single source file"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if file_path.endswith(".py"):
                await self._analyze_python_file(content, relative_path, graph)
            else:
                # For other languages, do basic analysis
                await self._analyze_generic_file(content, relative_path, graph)

        except Exception as e:
            logger.warning(f"Failed to analyze file {file_path}: {e}")

    async def _analyze_python_file(
        self, content: str, file_path: str, graph: nx.DiGraph
    ):
        """Analyze Python file using AST"""
        try:
            tree = ast.parse(content)

            # Add file node
            file_node = f"file:{file_path}"
            graph.add_node(
                file_node,
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content=content[:1000],
            )  # First 1000 chars

            # Analyze AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    await self._add_class_node(node, file_path, file_node, graph)
                elif isinstance(node, ast.FunctionDef):
                    await self._add_function_node(node, file_path, file_node, graph)
                elif isinstance(node, ast.Import):
                    await self._add_import_edges(node, file_node, graph)
                elif isinstance(node, ast.ImportFrom):
                    await self._add_import_from_edges(node, file_node, graph)

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error analyzing Python file {file_path}: {e}")

    async def _add_class_node(
        self, node: ast.ClassDef, file_path: str, file_node: str, graph: nx.DiGraph
    ):
        """Add class node to graph"""
        class_node = f"class:{file_path}:{node.name}"

        # Get docstring
        docstring = ast.get_docstring(node) or ""

        # Get base classes
        bases = [self._get_name(base) for base in node.bases]

        graph.add_node(
            class_node,
            type="class",
            name=node.name,
            file_path=file_path,
            docstring=docstring,
            bases=bases,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
        )

        # Connect to file
        graph.add_edge(file_node, class_node, type="contains")

        # Add methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                await self._add_method_node(item, file_path, class_node, graph)

    async def _add_function_node(
        self, node: ast.FunctionDef, file_path: str, parent_node: str, graph: nx.DiGraph
    ):
        """Add function node to graph"""
        func_node = f"function:{file_path}:{node.name}"

        # Get docstring
        docstring = ast.get_docstring(node) or ""

        # Get arguments
        args = [arg.arg for arg in node.args.args]

        graph.add_node(
            func_node,
            type="function",
            name=node.name,
            file_path=file_path,
            docstring=docstring,
            args=args,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
        )

        # Connect to parent (file or class)
        graph.add_edge(parent_node, func_node, type="contains")

    async def _add_method_node(
        self, node: ast.FunctionDef, file_path: str, class_node: str, graph: nx.DiGraph
    ):
        """Add method node to graph"""
        method_node = f"method:{file_path}:{node.name}"

        # Get docstring
        docstring = ast.get_docstring(node) or ""

        # Get arguments
        args = [arg.arg for arg in node.args.args]

        graph.add_node(
            method_node,
            type="method",
            name=node.name,
            file_path=file_path,
            docstring=docstring,
            args=args,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
        )

        # Connect to class
        graph.add_edge(class_node, method_node, type="contains")

    async def _add_import_edges(
        self, node: ast.Import, file_node: str, graph: nx.DiGraph
    ):
        """Add import relationships"""
        for alias in node.names:
            import_node = f"import:{alias.name}"
            if not graph.has_node(import_node):
                graph.add_node(import_node, type="import", name=alias.name)
            graph.add_edge(file_node, import_node, type="imports")

    async def _add_import_from_edges(
        self, node: ast.ImportFrom, file_node: str, graph: nx.DiGraph
    ):
        """Add import from relationships"""
        if node.module:
            for alias in node.names:
                import_node = f"import:{node.module}.{alias.name}"
                if not graph.has_node(import_node):
                    graph.add_node(
                        import_node, type="import", name=f"{node.module}.{alias.name}"
                    )
                graph.add_edge(file_node, import_node, type="imports")

    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return str(node)

    async def _analyze_generic_file(
        self, content: str, file_path: str, graph: nx.DiGraph
    ):
        """Basic analysis for non-Python files"""
        file_node = f"file:{file_path}"
        graph.add_node(
            file_node,
            type="file",
            name=os.path.basename(file_path),
            file_path=file_path,
            content=content[:1000],
        )  # First 1000 chars

    def _graph_to_dict(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Convert NetworkX graph to dictionary format"""
        nodes_data = []
        for node in graph.nodes():
            node_data = dict(graph.nodes[node])
            node_data["id"] = node
            nodes_data.append(node_data)

        edges_data = []
        for edge in graph.edges():
            edge_data = dict(graph.edges[edge])
            edge_data["source"] = edge[0]
            edge_data["target"] = edge[1]
            edges_data.append(edge_data)

        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "metadata": {
                "total_nodes": len(nodes_data),
                "total_edges": len(edges_data),
                "node_types": list(
                    set(node.get("type", "unknown") for node in nodes_data)
                ),
            },
        }

    def _create_empty_graph(self) -> Dict[str, Any]:
        """Create an empty graph structure"""
        return {
            "nodes": [],
            "edges": [],
            "metadata": {"total_nodes": 0, "total_edges": 0, "node_types": []},
        }

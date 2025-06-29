"""
Reader Component for CGM

Generates code patches based on subgraph and ranked files
"""

import re
from typing import Any, Dict, List, Optional

from loguru import logger

from ..models import CodePatch, ReaderRequest, ReaderResponse
from ..utils.llm_client import LLMClient


class ReaderComponent:
    """
    Reader component that generates code patches to resolve issues
    based on the retrieved subgraph and top-ranked files
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate_patch_prompt(
        self,
        problem_statement: str,
        subgraph: Dict[str, Any],
        top_files: List[str],
        repository_context: Dict[str, Any],
    ) -> str:
        """Generate prompt for code patch generation"""

        # Extract relevant information from subgraph
        subgraph_summary = self._summarize_subgraph(subgraph)

        # Format top files information
        files_info = "\n".join([f"- {file}" for file in top_files])

        prompt = f"""
You are an expert software engineer tasked with generating code patches to resolve repository issues.

<issue>
{problem_statement}
</issue>

<repository_context>
Repository: {repository_context.get('name', 'Unknown')}
Language: {repository_context.get('language', 'Python')}
Framework: {repository_context.get('framework', 'N/A')}
</repository_context>

<code_graph_context>
{subgraph_summary}
</code_graph_context>

<top_relevant_files>
{files_info}
</top_relevant_files>

Task:
Based on the issue description and the provided context, generate specific code patches that would resolve the issue.

Instructions:
1. Analysis:
   - Analyze the issue and identify the root cause
   - Determine which files need to be modified
   - Consider the relationships shown in the code graph
   
2. Patch Generation:
   - Generate specific code changes for each file that needs modification
   - Provide the exact code that should be added, modified, or removed
   - Include line numbers or context for where changes should be applied
   - Ensure changes are minimal and focused on the issue
   
3. Explanation:
   - Explain why each change is necessary
   - Describe how the changes resolve the issue
   - Consider potential side effects or dependencies

Respond in the following format:
[start_of_analysis]
<detailed_analysis_of_the_issue_and_solution_approach>
[end_of_analysis]

[start_of_patches]
PATCH 1:
File: <file_path>
Description: <brief_description_of_changes>
Line Range: <start_line>-<end_line>
Original Code:
```
<original_code_block>
```
Modified Code:
```
<modified_code_block>
```
Explanation: <explanation_of_why_this_change_is_needed>

PATCH 2:
...
[end_of_patches]

[start_of_summary]
<summary_of_all_changes_and_expected_impact>
[end_of_summary]

Notes:
- Focus on the most critical changes needed to resolve the issue
- Ensure code follows the project's existing style and conventions
- Consider error handling and edge cases
- Provide complete, working code blocks
"""

        return prompt

    def _summarize_subgraph(self, subgraph: Dict[str, Any]) -> str:
        """Create a summary of the code subgraph"""
        nodes = subgraph.get("nodes", [])
        edges = subgraph.get("edges", [])
        metadata = subgraph.get("metadata", {})

        summary_parts = []

        # Basic statistics
        summary_parts.append(f"Code Graph Summary:")
        summary_parts.append(f"- Total nodes: {len(nodes)}")
        summary_parts.append(f"- Total edges: {len(edges)}")
        summary_parts.append(
            f"- Anchor nodes: {', '.join(metadata.get('anchor_nodes', []))}"
        )

        # Key nodes information
        if nodes:
            summary_parts.append("\nKey Code Entities:")
            for node in nodes[:10]:  # Limit to top 10 nodes
                node_type = node.get("type", "unknown")
                node_name = node.get("name", node.get("id", "unnamed"))
                file_path = node.get("file_path", "unknown")

                summary_parts.append(f"- {node_type}: {node_name} (in {file_path})")

        # Relationships
        if edges:
            summary_parts.append(
                f"\nRelationships: {len(edges)} connections between code entities"
            )

        return "\n".join(summary_parts)

    def parse_patch_response(self, response: str) -> tuple[str, List[CodePatch], str]:
        """Parse the LLM response to extract patches"""
        try:
            # Extract analysis
            analysis_match = re.search(
                r"\[start_of_analysis\](.*?)\[end_of_analysis\]", response, re.DOTALL
            )
            analysis = analysis_match.group(1).strip() if analysis_match else ""

            # Extract summary
            summary_match = re.search(
                r"\[start_of_summary\](.*?)\[end_of_summary\]", response, re.DOTALL
            )
            summary = summary_match.group(1).strip() if summary_match else ""

            # Extract patches
            patches_match = re.search(
                r"\[start_of_patches\](.*?)\[end_of_patches\]", response, re.DOTALL
            )
            patches_text = patches_match.group(1).strip() if patches_match else ""

            patches = self._parse_individual_patches(patches_text)

            return analysis, patches, summary

        except Exception as e:
            logger.error(f"Error parsing patch response: {e}")
            return "", [], ""

    def _parse_individual_patches(self, patches_text: str) -> List[CodePatch]:
        """Parse individual patches from the patches text"""
        patches = []

        # Split by PATCH markers
        patch_blocks = re.split(r"PATCH\s+\d+:", patches_text)

        for block in patch_blocks[1:]:  # Skip first empty block
            try:
                patch = self._parse_single_patch(block)
                if patch:
                    patches.append(patch)
            except Exception as e:
                logger.warning(f"Failed to parse patch block: {e}")
                continue

        return patches

    def _parse_single_patch(self, patch_block: str) -> Optional[CodePatch]:
        """Parse a single patch block"""
        try:
            lines = patch_block.strip().split("\n")

            file_path = ""
            description = ""
            line_start = 1
            line_end = 1
            original_code = ""
            modified_code = ""
            explanation = ""

            current_section = None
            code_buffer = []

            for line in lines:
                line = line.strip()

                if line.startswith("File:"):
                    file_path = line.replace("File:", "").strip()
                elif line.startswith("Description:"):
                    description = line.replace("Description:", "").strip()
                elif line.startswith("Line Range:"):
                    range_text = line.replace("Line Range:", "").strip()
                    if "-" in range_text:
                        start, end = range_text.split("-")
                        line_start = int(start.strip())
                        line_end = int(end.strip())
                elif line.startswith("Original Code:"):
                    current_section = "original"
                    code_buffer = []
                elif line.startswith("Modified Code:"):
                    if current_section == "original":
                        original_code = "\n".join(code_buffer)
                    current_section = "modified"
                    code_buffer = []
                elif line.startswith("Explanation:"):
                    if current_section == "modified":
                        modified_code = "\n".join(code_buffer)
                    explanation = line.replace("Explanation:", "").strip()
                    current_section = "explanation"
                elif line.startswith("```"):
                    # Skip code block markers
                    continue
                elif current_section in ["original", "modified"]:
                    code_buffer.append(line)
                elif current_section == "explanation":
                    explanation += " " + line

            # Handle last section
            if current_section == "modified":
                modified_code = "\n".join(code_buffer)

            if file_path and (original_code or modified_code):
                return CodePatch(
                    file_path=file_path,
                    original_code=original_code,
                    modified_code=modified_code,
                    line_start=line_start,
                    line_end=line_end,
                    explanation=explanation or description,
                )

        except Exception as e:
            logger.error(f"Error parsing single patch: {e}")

        return None

    def calculate_confidence(self, patches: List[CodePatch], analysis: str) -> float:
        """Calculate confidence score for the generated patches"""
        confidence = 0.5  # Base confidence

        # Increase confidence based on number of patches
        if patches:
            confidence += min(0.2, len(patches) * 0.05)

        # Increase confidence if analysis is detailed
        if len(analysis) > 200:
            confidence += 0.1

        # Increase confidence if patches have explanations
        explained_patches = sum(1 for p in patches if p.explanation)
        if explained_patches > 0:
            confidence += 0.1 * (explained_patches / len(patches))

        # Increase confidence if patches modify different files
        unique_files = len(set(p.file_path for p in patches))
        if unique_files > 1:
            confidence += 0.1

        return min(1.0, confidence)

    async def process(self, request: ReaderRequest) -> ReaderResponse:
        """Process a reader request to generate code patches"""
        try:
            logger.info("Processing reader request")

            # Generate patch prompt
            prompt = self.generate_patch_prompt(
                request.problem_statement,
                request.subgraph,
                request.top_files,
                request.repository_context,
            )

            # Generate patches using LLM
            response = await self.llm_client.generate(prompt)

            # Parse response
            analysis, patches, summary = self.parse_patch_response(response)

            # Calculate confidence
            confidence = self.calculate_confidence(patches, analysis)

            logger.info(
                f"Reader generated {len(patches)} patches with confidence {confidence:.2f}"
            )

            return ReaderResponse(
                patches=patches, summary=summary, confidence=confidence
            )

        except Exception as e:
            logger.error(f"Error in reader processing: {e}")
            raise

"""
Reranker Component for CGM

Ranks files by relevance to the issue for focused analysis
"""

import re
from typing import Any, Dict, List, Tuple

from loguru import logger

from ..models import FileScore, RerankerRequest, RerankerResponse
from ..utils.llm_client import LLMClient


class RerankerComponent:
    """
    Reranker component that identifies the most relevant files
    for issue resolution using a two-stage ranking process
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate_prompt_for_stage_1(
        self,
        problem_statement: str,
        repo_name: str,
        py_files: List[str],
        other_files: List[str],
    ) -> Tuple[str, str]:
        """Generate prompt for stage 1 reranking (file selection)"""

        system_prompt = """
You are an experienced software developer who specializes in extracting the most relevant files for solving issues from many reference files.
Task:
Based on the information received about the issue from a repository, find the most likely few files from among those that may be able to resolve the issue.
Instructions:
1. Analysis:
- Analyze the provided issue description and files, and pay attention to the relevance of the provided files with the given issue, especially those might be modified during fixing the issue.
- Determine the specific problem or error mentioned in the issue and note any clues that could help your judgment.
2. Extraction:
- Based on your analysis, choose the Top **5** relevant files which might be used in fixing the issue.
- You should choose files from the provided files, and should not modify their name in any way.
Respond in the following format:
[start_of_analysis]
<detailed_analysis> 
[end_of_analysis] 
[start_of_relevant_files] 
1. <file_with_its_path>
2. <file_with_its_path>
3. ...
[end_of_relevant_files] 
Notes:
- You can refer to to the information in the error logs (if exists).
- The relevant file usually exists in the project described in the issue (e.g., django, sklearn). File need modification is usually not in the tests files or external packages.
- The file you choose should be contained in the provided files.
- Provide the file path with files. Do not include redundant suffix like '/home/username/', '/etc/service/' or '/tree/master'.
- Do not include any additional information such as line numbers or explanations in your extraction result.
- Files for initialization and configuration might be modified during changing the code.
Preferred extraction Examples of Related Files:
1. src/utils/file_handler.py
2. core/services/service_manager.py
3. ...
""".strip()

        user_prompt = f"""
<repository>
{repo_name}
</repository>
<issue>
{problem_statement}
</issue>
 
<reference_python_file_list>
{chr(10).join(py_files)}
</reference_python_file_list>
<other_reference_file_list>
{chr(10).join(other_files)}
</other_reference_file_list>
"""

        return system_prompt, user_prompt

    def generate_prompt_for_stage_2(
        self, problem_statement: str, repo_name: str, file_name: str, file_content: str
    ) -> Tuple[str, str]:
        """Generate prompt for stage 2 reranking (file scoring)"""

        system_prompt = """
You are an experienced software developer who specializes in assessing the relevance of the file for solving the issue in software repositories.
Task:
For a file provided, evaluate the likelihood that modifying this file would resolve the given issue, and assign a score based on specific criteria.
Instructions:
1. Analysis:
- Analyze the provided issue description and the content of the single relevant file, pay attention to any keywords, error messages, or specific functionalities mentioned that relate to the file.
- Determine how closely the contents and functionality of the file are tied to the problem or error described in the issue.
- Consider the role of the file in the overall project structure (e.g., configuration files, core logic files versus test files, or utility scripts).
2. Scoring:
- Based on your analysis, assign a score from 1 to 5 that represents the relevance of modifying the given file in order to solve the issue.
Score Specifications:
1. **Score 1**: The file is almost certainly unrelated to the issue, with no apparent connection to the functionality or error described in the issue.
2. **Score 2**: The file may be tangentially related, but modifying it is unlikely to resolve the issue directly; possible in rare edge cases.
3. **Score 3**: The file has some relevance to the issue; it might interact with the affected functionality indirectly and tweaking it could be part of a broader fix.
4. **Score 4**: The file is likely related to the issue; it includes code that interacts directly with the functionality in question and could plausibly contain bugs that lead to the issue.
5. **Score 5**: The file is very likely the root cause or heavily involved in the issue and modifying it should directly address the error or problem mentioned.
Respond in the following format:
[start_of_analysis]
<detailed_analysis>
[end_of_analysis]
[start_of_score]
Score <number>
[end_of_score]
Notes:
- The content of the file shows only the structure of this file, including the names of the classes and functions defined in this file.
- You can refer to to the information in the error logs (if exists).
""".strip()

        user_prompt = f"""
<repository>
{repo_name}
</repository>
<issue>
{problem_statement}
</issue>
<file_name>
{file_name}
</file_name>
<file_content>
{file_content}
</file_content>
"""

        return system_prompt, user_prompt

    def parse_stage_1_response(self, response: str) -> Tuple[str, List[str]]:
        """Parse the response from stage 1 reranking"""
        try:
            # Extract analysis
            analysis_match = re.search(
                r"\[start_of_analysis\](.*?)\[end_of_analysis\]", response, re.DOTALL
            )
            analysis = analysis_match.group(1).strip() if analysis_match else ""

            # Extract files
            files_match = re.search(
                r"\[start_of_relevant_files\](.*?)\[end_of_relevant_files\]",
                response,
                re.DOTALL,
            )
            files_text = files_match.group(1).strip() if files_match else ""

            # Parse numbered list
            files = []
            for line in files_text.split("\n"):
                line = line.strip()
                if line:
                    # Remove numbering (e.g., "1. ", "2. ")
                    file_path = re.sub(r"^\d+\.\s*", "", line)
                    if file_path:
                        files.append(file_path)

            return analysis, files

        except Exception as e:
            logger.error(f"Error parsing stage 1 response: {e}")
            return "", []

    def parse_stage_2_response(self, response: str) -> Tuple[str, int]:
        """Parse the response from stage 2 reranking"""
        try:
            # Extract analysis
            analysis_match = re.search(
                r"\[start_of_analysis\](.*?)\[end_of_analysis\]", response, re.DOTALL
            )
            analysis = analysis_match.group(1).strip() if analysis_match else ""

            # Extract score
            score_match = re.search(
                r"\[start_of_score\].*?Score\s+(\d+).*?\[end_of_score\]",
                response,
                re.DOTALL | re.IGNORECASE,
            )
            score = (
                int(score_match.group(1)) if score_match else 3
            )  # Default to middle score

            # Ensure score is in valid range
            score = max(1, min(5, score))

            return analysis, score

        except Exception as e:
            logger.error(f"Error parsing stage 2 response: {e}")
            return "", 3

    def get_file_structure(self, file_content: str) -> str:
        """Extract file structure (classes and functions) from file content"""
        # This is a simplified version - in practice, you'd use AST parsing
        structure_lines = []

        for line in file_content.split("\n"):
            line = line.strip()
            if line.startswith("class ") or line.startswith("def "):
                structure_lines.append(line)

        return "\n".join(structure_lines) if structure_lines else file_content[:500]

    async def process(self, request: RerankerRequest) -> RerankerResponse:
        """Process a reranker request"""
        try:
            logger.info("Processing reranker request")

            all_files = request.python_files + request.other_files

            if not all_files:
                return RerankerResponse(top_files=[], file_scores=[])

            # Stage 1: Select top relevant files
            system_prompt, user_prompt = self.generate_prompt_for_stage_1(
                request.problem_statement,
                request.repo_name,
                request.python_files,
                request.other_files,
            )

            stage_1_response = await self.llm_client.generate(
                f"{system_prompt}\n\n{user_prompt}"
            )

            analysis, top_files = self.parse_stage_1_response(stage_1_response)

            # Filter to only include files that exist in the request
            valid_top_files = [f for f in top_files if f in all_files]

            logger.info(f"Stage 1 selected {len(valid_top_files)} files")

            # Stage 2: Score each selected file
            file_scores = []

            for file_path in valid_top_files:
                file_content = request.file_contents.get(file_path, "")

                # Get file structure for scoring
                file_structure = self.get_file_structure(file_content)

                system_prompt, user_prompt = self.generate_prompt_for_stage_2(
                    request.problem_statement,
                    request.repo_name,
                    file_path,
                    file_structure,
                )

                stage_2_response = await self.llm_client.generate(
                    f"{system_prompt}\n\n{user_prompt}"
                )

                file_analysis, score = self.parse_stage_2_response(stage_2_response)

                file_scores.append(
                    FileScore(file_path=file_path, score=score, analysis=file_analysis)
                )

            # Sort by score (highest first)
            file_scores.sort(key=lambda x: x.score, reverse=True)

            # Get top files based on scores
            final_top_files = [fs.file_path for fs in file_scores[:5]]

            logger.info(f"Reranker completed with {len(final_top_files)} top files")

            return RerankerResponse(top_files=final_top_files, file_scores=file_scores)

        except Exception as e:
            logger.error(f"Error in reranker processing: {e}")
            raise

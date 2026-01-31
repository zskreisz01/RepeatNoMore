"""Draft suggestion agent using RAG and LLM to analyze documentation change requests."""

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.config import get_settings
from app.llm import BaseLLMProvider, LLMMessage, LLMOptions, get_llm_provider
from app.rag.retriever import get_retriever
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DraftSuggestion:
    """Structured draft suggestion from LLM analysis."""
    target_file: str
    target_section: str
    change_type: str  # "add", "modify", "delete"
    suggested_content: str
    rationale: str
    requires_mkdocs_update: bool
    mkdocs_changes: Optional[str] = None
    confidence: float = 0.0


class DraftSuggestionAgent:
    """Agent that analyzes documentation change suggestions and creates structured drafts."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        """
        Initialize the draft suggestion agent.

        Args:
            llm_provider: Optional LLM provider instance. If not provided,
                         the default provider from settings will be used.
        """
        self.settings = get_settings()
        self.retriever = get_retriever()
        self.system_prompt = self._build_system_prompt()

        # Use injected provider or get default from settings
        self._llm = llm_provider or get_llm_provider()

        logger.info(
            "Draft Suggestion Agent initialized",
            provider=self._llm.provider_name,
            model=self._llm.model_name,
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt for analyzing documentation suggestions."""
        return """You are a documentation analysis assistant. Your task is to analyze user suggestions for documentation changes and create structured, actionable draft proposals.

When a user suggests a documentation change, you must:
1. Identify the most relevant existing documentation file(s) that should be modified
2. Determine the specific section or location within the file
3. Classify the change type (add new content, modify existing, or delete)
4. Generate the actual content that should be added or modified
5. Determine if mkdocs.yml navigation needs updating

IMPORTANT: You MUST respond with valid JSON in the following format:
{
    "target_file": "path/to/file.md",
    "target_section": "Section name or heading",
    "change_type": "add|modify|delete",
    "suggested_content": "The actual markdown content to add or the modified content",
    "rationale": "Brief explanation of why this change is appropriate",
    "requires_mkdocs_update": true|false,
    "mkdocs_changes": "Description of mkdocs.yml changes needed, or null if none"
}

Guidelines:
- Use the context from existing documentation to understand the structure and style
- Match the existing documentation style and formatting
- Be specific about file paths (use paths found in the context)
- For new content, place it in the most logical location
- If creating entirely new content that doesn't fit existing files, suggest a new file path
- Only suggest mkdocs.yml changes if adding a new page or restructuring navigation

ALWAYS respond with valid JSON only. No other text before or after the JSON.
Do NOT use <think> tags or reasoning blocks - output ONLY the JSON."""

    def _get_available_docs_context(self) -> str:
        """Get context about available documentation files."""
        # Use retriever to get a broad overview of docs
        try:
            result = self.retriever.retrieve_with_context(
                query="documentation structure overview files sections",
                top_k=10
            )
            return result.get("context", "")
        except Exception as e:
            logger.warning("failed_to_get_docs_context", error=str(e))
            return ""

    def _build_analysis_prompt(
        self,
        suggestion: str,
        context: str,
        additional_context: str = ""
    ) -> str:
        """Build the prompt for analyzing a documentation suggestion."""
        return f"""# Existing Documentation Context
{context}

{f"# Additional Context{chr(10)}{additional_context}" if additional_context else ""}

# User's Documentation Suggestion
{suggestion}

# Task
Analyze the user's suggestion and create a structured draft proposal. Determine:
1. Which existing file should be modified (or if a new file is needed)
2. Where in the file the change should go
3. What type of change this is (add/modify/delete)
4. The actual content to be added or modified
5. Whether mkdocs.yml navigation needs updating

Respond with valid JSON only."""

    def _parse_json_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling various edge cases."""
        json_str = raw_response.strip() if raw_response else ""

        # Handle Qwen3 thinking mode - strip <think>...</think> tags
        if "<think>" in json_str:
            json_str = re.sub(r"<think>.*?</think>", "", json_str, flags=re.DOTALL).strip()

        if not json_str:
            raise json.JSONDecodeError("Empty response from LLM", "", 0)

        # Handle case where LLM wraps JSON in markdown code block
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```json") or line.strip() == "```json":
                    in_json = True
                    continue
                elif line.startswith("```"):
                    in_json = False
                    continue
                if in_json:
                    json_lines.append(line)
            json_str = "\n".join(json_lines)

        # Try to find JSON object in the response if it's mixed with text
        if not json_str.startswith("{"):
            start_idx = json_str.find("{")
            end_idx = json_str.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = json_str[start_idx:end_idx]

        return json.loads(json_str)

    def analyze_suggestion(
        self,
        suggestion: str,
        context_query: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Analyze a documentation change suggestion and create a structured draft.

        Args:
            suggestion: User's description of the documentation change they want
            context_query: Optional specific query to find relevant docs
            temperature: LLM temperature (lower = more focused)
            max_tokens: Maximum tokens to generate

        Returns:
            Dict containing:
                - success: Whether analysis succeeded
                - draft: DraftSuggestion object if successful
                - raw_response: Raw LLM response
                - error: Error message if failed
        """
        start_time = time.time()

        if not suggestion or not suggestion.strip():
            return {"success": False, "error": "Suggestion cannot be empty"}

        logger.info("analyzing_suggestion", suggestion=suggestion[:100])

        try:
            # Step 1: Retrieve relevant documentation context
            query = context_query or suggestion
            retrieval_result = self.retriever.retrieve_with_context(
                query=query,
                top_k=8
            )
            context = retrieval_result.get("context", "")
            sources = retrieval_result.get("sources", [])

            logger.info("context_retrieved", num_sources=len(sources))

            # Step 2: Get additional overview context
            overview_context = self._get_available_docs_context()

            # Step 3: Build prompt
            prompt = self._build_analysis_prompt(suggestion, context, overview_context)

            # Step 4: Get LLM analysis
            logger.info(
                "generating_draft_analysis",
                provider=self._llm.provider_name,
                model=self._llm.model_name,
            )

            messages = [
                LLMMessage(role="system", content=self.system_prompt),
                LLMMessage(role="user", content=prompt),
            ]
            options = LLMOptions(
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response = self._llm.chat(messages, options)
            raw_response = response.content

            logger.debug(
                "llm_raw_response",
                response=raw_response[:500] if raw_response else "(empty)",
            )

            # Step 5: Parse JSON response
            try:
                parsed = self._parse_json_response(raw_response)

                draft = DraftSuggestion(
                    target_file=parsed.get("target_file", "docs/new_content.md"),
                    target_section=parsed.get("target_section", "New Section"),
                    change_type=parsed.get("change_type", "add"),
                    suggested_content=parsed.get("suggested_content", ""),
                    rationale=parsed.get("rationale", ""),
                    requires_mkdocs_update=parsed.get("requires_mkdocs_update", False),
                    mkdocs_changes=parsed.get("mkdocs_changes"),
                    confidence=0.8 if sources else 0.5
                )

                processing_time = time.time() - start_time
                logger.info(
                    "draft_analysis_complete",
                    target_file=draft.target_file,
                    change_type=draft.change_type,
                    processing_time=processing_time
                )

                return {
                    "success": True,
                    "draft": draft,
                    "raw_response": raw_response,
                    "sources": sources,
                    "processing_time": processing_time
                }

            except json.JSONDecodeError as e:
                logger.error("json_parse_failed", error=str(e), response=raw_response[:200])
                # Return a fallback draft with the raw content
                return {
                    "success": True,
                    "draft": DraftSuggestion(
                        target_file="docs/suggestions.md",
                        target_section="User Suggestion",
                        change_type="add",
                        suggested_content=suggestion,
                        rationale="Could not parse LLM response; storing raw suggestion",
                        requires_mkdocs_update=False,
                        confidence=0.3
                    ),
                    "raw_response": raw_response,
                    "sources": sources,
                    "parse_error": str(e)
                }

        except Exception as e:
            logger.error("draft_analysis_failed", error=str(e))
            return {"success": False, "error": str(e)}

    def refine_suggestion(
        self,
        original_draft: DraftSuggestion,
        feedback: str,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Refine a draft suggestion based on feedback.

        Args:
            original_draft: The original draft suggestion
            feedback: User or admin feedback for refinement

        Returns:
            Dict with refined draft suggestion
        """
        refinement_prompt = f"""# Original Draft
Target File: {original_draft.target_file}
Target Section: {original_draft.target_section}
Change Type: {original_draft.change_type}
Content:
{original_draft.suggested_content}

Rationale: {original_draft.rationale}

# Feedback
{feedback}

# Task
Refine the draft based on the feedback provided. Maintain the same JSON response format."""

        try:
            messages = [
                LLMMessage(role="system", content=self.system_prompt),
                LLMMessage(role="user", content=refinement_prompt),
            ]
            options = LLMOptions(temperature=temperature)

            response = self._llm.chat(messages, options)
            raw_response = response.content

            parsed = self._parse_json_response(raw_response)

            refined_draft = DraftSuggestion(
                target_file=parsed.get("target_file", original_draft.target_file),
                target_section=parsed.get("target_section", original_draft.target_section),
                change_type=parsed.get("change_type", original_draft.change_type),
                suggested_content=parsed.get("suggested_content", original_draft.suggested_content),
                rationale=parsed.get("rationale", "Refined based on feedback"),
                requires_mkdocs_update=parsed.get("requires_mkdocs_update", False),
                mkdocs_changes=parsed.get("mkdocs_changes"),
                confidence=original_draft.confidence
            )

            return {"success": True, "draft": refined_draft}

        except Exception as e:
            logger.error("draft_refinement_failed", error=str(e))
            return {"success": False, "error": str(e), "draft": original_draft}

    def edit_content(
        self,
        current_content: str,
        edit_instruction: str,
        target_file: str = "",
        target_section: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Edit content based on natural language instruction.

        Args:
            current_content: The current draft content to modify
            edit_instruction: Natural language instruction for how to modify the content
            target_file: Optional file context for better editing
            target_section: Optional section context for better editing
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Dict containing:
                - success: Whether edit succeeded
                - content: The modified content
                - changes_summary: Brief summary of changes made
                - error: Error message if failed
        """
        start_time = time.time()

        if not current_content or not current_content.strip():
            return {"success": False, "error": "Current content cannot be empty"}

        if not edit_instruction or not edit_instruction.strip():
            return {"success": False, "error": "Edit instruction cannot be empty"}

        logger.info(
            "editing_draft_content",
            instruction=edit_instruction[:100],
            content_length=len(current_content)
        )

        edit_system_prompt = """You are a documentation editor. Your task is to modify the given content based on the user's instruction.

IMPORTANT: You MUST respond with valid JSON in the following format:
{
    "modified_content": "The full modified content with the changes applied",
    "changes_summary": "Brief summary of what was changed (1-2 sentences)"
}

Guidelines:
- Apply the requested changes while preserving the overall structure and style
- Keep formatting consistent (markdown, indentation, etc.)
- Only modify what's necessary based on the instruction
- If the instruction is unclear, make reasonable assumptions
- Preserve any code blocks, links, or special formatting

ALWAYS respond with valid JSON only. No other text before or after the JSON."""

        context_info = ""
        if target_file:
            context_info += f"**Target File:** {target_file}\n"
        if target_section:
            context_info += f"**Target Section:** {target_section}\n"

        edit_prompt = f"""# Current Content
{current_content}

{f"# Context{chr(10)}{context_info}" if context_info else ""}
# Edit Instruction
{edit_instruction}

# Task
Apply the edit instruction to the current content and return the modified version."""

        try:
            logger.info(
                "generating_content_edit",
                provider=self._llm.provider_name,
                model=self._llm.model_name,
            )

            messages = [
                LLMMessage(role="system", content=edit_system_prompt),
                LLMMessage(role="user", content=edit_prompt),
            ]
            options = LLMOptions(
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response = self._llm.chat(messages, options)
            raw_response = response.content

            logger.debug(
                "llm_edit_response",
                response=raw_response[:500] if raw_response else "(empty)",
            )

            # Try to parse JSON, with fallback for malformed responses
            try:
                parsed = self._parse_json_response(raw_response)
                modified_content = parsed.get("modified_content", "")
                changes_summary = parsed.get(
                    "changes_summary", "Content modified based on instruction"
                )
            except json.JSONDecodeError:
                # Fallback: try to extract content using regex
                logger.warning(
                    "json_parse_failed_trying_regex",
                    json_preview=raw_response[:200] if raw_response else "(empty)",
                )

                json_str = raw_response.strip() if raw_response else ""

                # Try to extract modified_content value
                content_match = re.search(
                    r'"modified_content"\s*:\s*"((?:[^"\\]|\\.)*)"|"modified_content"\s*:\s*`((?:[^`])*)`',
                    json_str,
                    re.DOTALL,
                )
                summary_match = re.search(
                    r'"changes_summary"\s*:\s*"((?:[^"\\]|\\.)*)"',
                    json_str,
                    re.DOTALL,
                )

                if content_match:
                    modified_content = content_match.group(1) or content_match.group(2) or ""
                    # Unescape common escape sequences
                    modified_content = (
                        modified_content.replace("\\n", "\n")
                        .replace("\\t", "\t")
                        .replace('\\"', '"')
                    )
                    changes_summary = (
                        summary_match.group(1) if summary_match else "Content modified"
                    )
                else:
                    # Last resort: if it looks like the LLM just returned the modified content directly
                    # (without JSON wrapper), use that
                    if not json_str.startswith("{") or "modified_content" not in json_str:
                        # Check if response looks like documentation content
                        if (
                            len(json_str) > 50
                            and ("##" in json_str or "```" in json_str or "\n" in json_str)
                        ):
                            logger.warning("using_raw_response_as_content")
                            modified_content = json_str
                            changes_summary = "Content modified (raw LLM output)"
                        else:
                            raise json.JSONDecodeError(
                                "Could not extract content from response", json_str, 0
                            )
                    else:
                        raise

            if not modified_content:
                return {
                    "success": False,
                    "error": "LLM returned empty modified content"
                }

            processing_time = time.time() - start_time
            logger.info(
                "content_edit_complete",
                changes_summary=changes_summary,
                processing_time=processing_time
            )

            return {
                "success": True,
                "content": modified_content,
                "changes_summary": changes_summary,
                "processing_time": processing_time
            }

        except json.JSONDecodeError as e:
            logger.error("edit_json_parse_failed", error=str(e), response=raw_response[:200] if raw_response else "(empty)")
            return {
                "success": False,
                "error": f"Failed to parse LLM response: {str(e)}"
            }
        except Exception as e:
            logger.error("content_edit_failed", error=str(e))
            return {"success": False, "error": str(e)}


# Global instance
_draft_agent: Optional[DraftSuggestionAgent] = None


def get_draft_agent() -> DraftSuggestionAgent:
    """Get or create a global draft suggestion agent instance."""
    global _draft_agent
    if _draft_agent is None:
        _draft_agent = DraftSuggestionAgent()
    return _draft_agent

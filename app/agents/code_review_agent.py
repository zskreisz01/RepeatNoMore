"""Code review agent for analyzing code and providing feedback."""

import time
from typing import Any, Dict, List, Optional

from app.agents.shared import (
    AgentResult,
    AgentStatus,
    AgentType,
    BaseAgent,
    PromptBuilder,
    ResponseFormatter,
    extract_code_blocks,
)
from app.config import get_settings
from app.llm import BaseLLMProvider, LLMMessage, LLMOptions, get_llm_provider
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CodeReviewAgent(BaseAgent):
    """Agent for reviewing code and providing feedback."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        """
        Initialize the code review agent.

        Args:
            llm_provider: Optional LLM provider instance. If not provided,
                         the default provider from settings will be used.
        """
        super().__init__(AgentType.CODE_REVIEW)
        self.settings = get_settings()
        self.system_prompt = self._build_system_prompt()

        # Use injected provider or get default from settings
        self._llm = llm_provider or get_llm_provider()

        logger.info(
            "code_review_agent_initialized",
            provider=self._llm.provider_name,
            model=self._llm.model_name,
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt for code review."""
        return PromptBuilder.build_system_prompt(
            role="an expert code reviewer with deep knowledge of software engineering best practices",
            capabilities=[
                "Analyze code for bugs, security vulnerabilities, and performance issues",
                "Check code style and adherence to best practices",
                "Suggest improvements and refactoring opportunities",
                "Identify potential edge cases and error handling issues",
                "Evaluate code maintainability and readability"
            ],
            guidelines=[
                "Be constructive and specific in feedback",
                "Prioritize issues by severity (error, warning, info)",
                "Provide concrete examples and suggestions",
                "Focus on both correctness and code quality",
                "Consider security implications",
                "Be concise but thorough"
            ]
        )

    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Review code and provide feedback.

        Args:
            input_data: Dictionary containing:
                - code: Code to review (required)
                - language: Programming language (optional)
                - context: Additional context (optional)
                - focus_areas: Specific areas to focus on (optional)

        Returns:
            AgentResult: Review results with findings and suggestions
        """
        start_time = time.time()
        self._set_status(AgentStatus.PROCESSING)

        try:
            # Validate input
            self._validate_input(input_data, ["code"])

            code = input_data["code"]
            language = input_data.get("language", "unknown")
            context = input_data.get("context", "")
            focus_areas = input_data.get("focus_areas", [])

            logger.info(
                "reviewing_code",
                language=language,
                code_length=len(code),
                has_context=bool(context)
            )

            # Build review prompt
            prompt = self._build_review_prompt(code, language, context, focus_areas)

            # Get review from LLM
            messages = [
                LLMMessage(role="system", content=self.system_prompt),
                LLMMessage(role="user", content=prompt),
            ]
            options = LLMOptions(
                temperature=0.3,  # Lower temperature for more focused reviews
                max_tokens=2000,
            )

            response = self._llm.chat(messages, options)
            review = response.content

            # Parse review into structured format
            parsed_review = self._parse_review(review)

            processing_time = time.time() - start_time
            self._set_status(AgentStatus.COMPLETED)

            logger.info(
                "code_review_completed",
                processing_time=processing_time,
                findings_count=len(parsed_review.get("findings", []))
            )

            return AgentResult(
                success=True,
                output={
                    "review": review,
                    "structured_findings": parsed_review,
                    "language": language
                },
                metadata={
                    "code_length": len(code),
                    "language": language,
                    "findings_count": len(parsed_review.get("findings", []))
                },
                processing_time=processing_time
            )

        except Exception as e:
            self._set_status(AgentStatus.FAILED)
            logger.error("code_review_failed", error=str(e))

            return AgentResult(
                success=False,
                output=None,
                metadata={},
                error=str(e),
                processing_time=time.time() - start_time
            )

    def _build_review_prompt(
        self,
        code: str,
        language: str,
        context: str,
        focus_areas: List[str]
    ) -> str:
        """Build the prompt for code review."""
        prompt = f"Please review the following {language} code:\n\n"
        prompt += PromptBuilder.format_code_block(code, language)
        prompt += "\n"

        if context:
            prompt += f"\n**Context:** {context}\n\n"

        if focus_areas:
            prompt += "\n**Focus Areas:**\n"
            prompt += ResponseFormatter.format_list(focus_areas, numbered=False)
            prompt += "\n"

        prompt += """
Please provide a comprehensive code review covering:

1. **Bugs and Errors**: Identify any bugs or logical errors
2. **Security**: Check for security vulnerabilities
3. **Performance**: Suggest performance improvements
4. **Best Practices**: Adherence to coding standards and best practices
5. **Maintainability**: Code readability and maintainability issues
6. **Error Handling**: Proper error handling and edge cases

Format your response with:
- Clear severity levels (ERROR, WARNING, INFO)
- Specific line references where applicable
- Concrete suggestions for improvement
- Code examples for fixes when helpful
"""

        return prompt

    def _parse_review(self, review: str) -> Dict[str, Any]:
        """
        Parse review text into structured format.

        Args:
            review: Raw review text from LLM

        Returns:
            Dict with structured findings
        """
        # Extract severity levels
        findings = []

        for line in review.split("\n"):
            line = line.strip()

            # Look for severity indicators
            severity = None
            if "ERROR" in line.upper() or "🔴" in line:
                severity = "error"
            elif "WARNING" in line.upper() or "🟡" in line:
                severity = "warning"
            elif "INFO" in line.upper() or "🔵" in line:
                severity = "info"

            if severity:
                findings.append({
                    "severity": severity,
                    "description": line
                })

        # Extract code suggestions
        code_suggestions = extract_code_blocks(review)

        return {
            "findings": findings,
            "code_suggestions": code_suggestions,
            "raw_review": review
        }

    def review_file(self, file_path: str, **kwargs) -> AgentResult:
        """
        Review code from a file.

        Args:
            file_path: Path to code file
            **kwargs: Additional arguments passed to process()

        Returns:
            AgentResult: Review results
        """
        try:
            with open(file_path, 'r') as f:
                code = f.read()

            # Detect language from extension
            import os
            ext = os.path.splitext(file_path)[1]
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.go': 'go',
                '.rs': 'rust',
                '.rb': 'ruby',
            }
            language = language_map.get(ext, 'unknown')

            return self.process({
                "code": code,
                "language": language,
                **kwargs
            })

        except FileNotFoundError:
            return AgentResult(
                success=False,
                output=None,
                metadata={},
                error=f"File not found: {file_path}"
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output=None,
                metadata={},
                error=f"Failed to review file: {str(e)}"
            )

    def quick_check(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Quick code check focusing on critical issues.

        Args:
            code: Code to check
            language: Programming language

        Returns:
            Dict with quick check results
        """
        result = self.process({
            "code": code,
            "language": language,
            "focus_areas": ["bugs", "security", "critical errors"]
        })

        if result.success:
            findings = result.output["structured_findings"]["findings"]
            critical = [f for f in findings if f["severity"] == "error"]

            return {
                "has_critical_issues": len(critical) > 0,
                "critical_count": len(critical),
                "total_findings": len(findings),
                "critical_issues": critical
            }

        return {
            "has_critical_issues": False,
            "critical_count": 0,
            "total_findings": 0,
            "error": result.error
        }


# Global instance
_code_review_agent: Optional[CodeReviewAgent] = None


def get_code_review_agent() -> CodeReviewAgent:
    """
    Get or create a global code review agent instance.

    Returns:
        CodeReviewAgent: The code review agent
    """
    global _code_review_agent
    if _code_review_agent is None:
        _code_review_agent = CodeReviewAgent()
    return _code_review_agent

"""Benchmark tests for comparing different LLM models.

This module provides comprehensive benchmarks for testing different Ollama models,
measuring response times, token throughput, and quality metrics.

Usage:
    pytest tests/benchmark/test_model_benchmark.py -v --benchmark
    pytest tests/benchmark/test_model_benchmark.py::TestModelBenchmark -v -s

Environment Variables:
    BENCHMARK_MODELS: Comma-separated list of models to test (default: mistral:7b-instruct)
    BENCHMARK_ITERATIONS: Number of iterations per test (default: 3)
"""

import json
import os
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pytest

import ollama
from app.config import get_settings
from app.agents.qa_agent import QAAgent
from app.rag.retriever import get_retriever
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""

    model: str
    test_name: str
    iterations: int
    total_time: float
    llm_times: list[float] = field(default_factory=list)
    token_counts: list[dict[str, int]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def avg_llm_time(self) -> float:
        """Average LLM response time."""
        return statistics.mean(self.llm_times) if self.llm_times else 0.0

    @property
    def min_llm_time(self) -> float:
        """Minimum LLM response time."""
        return min(self.llm_times) if self.llm_times else 0.0

    @property
    def max_llm_time(self) -> float:
        """Maximum LLM response time."""
        return max(self.llm_times) if self.llm_times else 0.0

    @property
    def std_dev(self) -> float:
        """Standard deviation of LLM response times."""
        return statistics.stdev(self.llm_times) if len(self.llm_times) > 1 else 0.0

    @property
    def avg_prompt_tokens(self) -> float:
        """Average prompt tokens per request."""
        if not self.token_counts:
            return 0.0
        return statistics.mean(t.get("prompt", 0) for t in self.token_counts)

    @property
    def avg_completion_tokens(self) -> float:
        """Average completion tokens per request."""
        if not self.token_counts:
            return 0.0
        return statistics.mean(t.get("completion", 0) for t in self.token_counts)

    @property
    def tokens_per_second(self) -> float:
        """Average tokens generated per second."""
        if not self.token_counts or not self.llm_times:
            return 0.0
        total_tokens = sum(t.get("completion", 0) for t in self.token_counts)
        total_time = sum(self.llm_times)
        return total_tokens / total_time if total_time > 0 else 0.0

    @property
    def success_rate(self) -> float:
        """Percentage of successful iterations."""
        successful = len(self.llm_times)
        return (successful / self.iterations * 100) if self.iterations > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model": self.model,
            "test_name": self.test_name,
            "iterations": self.iterations,
            "total_time": round(self.total_time, 3),
            "avg_llm_time": round(self.avg_llm_time, 3),
            "min_llm_time": round(self.min_llm_time, 3),
            "max_llm_time": round(self.max_llm_time, 3),
            "std_dev": round(self.std_dev, 3),
            "avg_prompt_tokens": round(self.avg_prompt_tokens, 1),
            "avg_completion_tokens": round(self.avg_completion_tokens, 1),
            "tokens_per_second": round(self.tokens_per_second, 2),
            "success_rate": round(self.success_rate, 1),
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


class ModelBenchmarker:
    """Utility class for running model benchmarks."""

    # Test prompts of varying complexity
    TEST_PROMPTS = {
        "simple": "What is Python?",
        "medium": "Explain the difference between REST and GraphQL APIs, including their pros and cons.",
        "complex": """You are a software architect. Given a system that needs to handle
        10,000 concurrent users with real-time updates, what architecture would you recommend?
        Consider scalability, fault tolerance, and cost. Provide specific technology choices.""",
        "code": "Write a Python function that implements binary search on a sorted list.",
    }

    def __init__(self, models: list[str], iterations: int = 3):
        """
        Initialize benchmarker.

        Args:
            models: List of Ollama model names to benchmark
            iterations: Number of iterations per test
        """
        self.models = models
        self.iterations = iterations
        self.settings = get_settings()
        self.results: list[BenchmarkResult] = []

    def check_model_available(self, model: str) -> bool:
        """Check if a model is available in Ollama."""
        try:
            available_models = ollama.list()
            # Handle both dict (older versions) and Pydantic model (newer versions)
            models_list = available_models.get("models", []) if isinstance(available_models, dict) else getattr(available_models, "models", [])
            model_names = []
            for m in models_list:
                # Handle both dict and Pydantic model
                name = m.get("name") if isinstance(m, dict) else getattr(m, "model", None)
                if name:
                    model_names.append(name)
            # Check for exact match or prefix match (e.g., "mistral:7b" matches "mistral:7b-instruct")
            return any(model in name or name.startswith(model.split(":")[0]) for name in model_names)
        except Exception as e:
            logger.error("ollama_check_failed", error=str(e))
            return False

    def run_single_inference(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> tuple[str, float, dict[str, int] | None]:
        """
        Run a single inference and return timing info.

        Args:
            model: Model name
            prompt: Input prompt
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Tuple of (response_text, duration_seconds, token_counts)
        """
        start_time = time.time()

        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        )

        duration = time.time() - start_time
        answer = response["message"]["content"]

        # Extract token counts
        tokens = None
        if "prompt_eval_count" in response or "eval_count" in response:
            tokens = {
                "prompt": response.get("prompt_eval_count", 0),
                "completion": response.get("eval_count", 0),
            }

        return answer, duration, tokens

    def benchmark_model(self, model: str, prompt_type: str = "medium") -> BenchmarkResult:
        """
        Run benchmark for a single model.

        Args:
            model: Model name
            prompt_type: Type of prompt ("simple", "medium", "complex", "code")

        Returns:
            BenchmarkResult with timing statistics
        """
        prompt = self.TEST_PROMPTS.get(prompt_type, self.TEST_PROMPTS["medium"])
        result = BenchmarkResult(
            model=model,
            test_name=f"benchmark_{prompt_type}",
            iterations=self.iterations,
            total_time=0.0,
        )

        total_start = time.time()

        for i in range(self.iterations):
            try:
                logger.info(
                    "benchmark_iteration",
                    model=model,
                    prompt_type=prompt_type,
                    iteration=i + 1,
                    total=self.iterations,
                )

                _, duration, tokens = self.run_single_inference(model, prompt)
                result.llm_times.append(duration)
                if tokens:
                    result.token_counts.append(tokens)

                logger.info(
                    "benchmark_iteration_complete",
                    model=model,
                    iteration=i + 1,
                    duration=round(duration, 3),
                    tokens=tokens,
                )

            except Exception as e:
                error_msg = f"Iteration {i + 1} failed: {str(e)}"
                result.errors.append(error_msg)
                logger.error("benchmark_iteration_failed", model=model, iteration=i + 1, error=str(e))

        result.total_time = time.time() - total_start
        self.results.append(result)

        return result

    def benchmark_all(self, prompt_types: list[str] | None = None) -> list[BenchmarkResult]:
        """
        Run benchmarks for all models.

        Args:
            prompt_types: List of prompt types to test (default: all)

        Returns:
            List of BenchmarkResult objects
        """
        if prompt_types is None:
            prompt_types = list(self.TEST_PROMPTS.keys())

        for model in self.models:
            if not self.check_model_available(model):
                logger.warning("model_not_available", model=model)
                continue

            for prompt_type in prompt_types:
                self.benchmark_model(model, prompt_type)

        return self.results

    def save_results(self, output_path: str | Path) -> None:
        """Save benchmark results to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "models": self.models,
            "iterations": self.iterations,
            "results": [r.to_dict() for r in self.results],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("benchmark_results_saved", path=str(output_path))

    def print_summary(self) -> None:
        """Print a summary of benchmark results."""
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS SUMMARY")
        print("=" * 80)

        for result in self.results:
            print(f"\nModel: {result.model}")
            print(f"Test: {result.test_name}")
            print(f"Iterations: {result.iterations} (Success Rate: {result.success_rate:.1f}%)")
            print(f"Avg LLM Time: {result.avg_llm_time:.3f}s (min: {result.min_llm_time:.3f}s, max: {result.max_llm_time:.3f}s)")
            print(f"Std Dev: {result.std_dev:.3f}s")
            print(f"Tokens/sec: {result.tokens_per_second:.2f}")
            print(f"Avg Prompt Tokens: {result.avg_prompt_tokens:.1f}")
            print(f"Avg Completion Tokens: {result.avg_completion_tokens:.1f}")
            if result.errors:
                print(f"Errors: {len(result.errors)}")
            print("-" * 40)


def get_benchmark_models() -> list[str]:
    """Get list of models to benchmark from environment or default."""
    models_env = os.environ.get("BENCHMARK_MODELS", "")
    if models_env:
        return [m.strip() for m in models_env.split(",") if m.strip()]

    # Default to configured model
    settings = get_settings()
    return [settings.ollama_model]


def get_benchmark_iterations() -> int:
    """Get number of benchmark iterations from environment or default."""
    try:
        return int(os.environ.get("BENCHMARK_ITERATIONS", "3"))
    except ValueError:
        return 3


@pytest.fixture(scope="module")
def benchmark_models() -> list[str]:
    """Fixture providing list of models to benchmark."""
    return get_benchmark_models()


@pytest.fixture(scope="module")
def benchmark_iterations() -> int:
    """Fixture providing number of iterations."""
    return get_benchmark_iterations()


@pytest.fixture(scope="module")
def benchmarker(benchmark_models: list[str], benchmark_iterations: int) -> ModelBenchmarker:
    """Fixture providing initialized benchmarker."""
    return ModelBenchmarker(models=benchmark_models, iterations=benchmark_iterations)


def check_ollama_available() -> bool:
    """Check if Ollama service is available."""
    try:
        ollama.list()
        return True
    except Exception:
        return False


@pytest.mark.benchmark
@pytest.mark.slow
class TestModelBenchmark:
    """Benchmark tests for LLM models."""

    @pytest.fixture(autouse=True)
    def skip_if_ollama_unavailable(self):
        """Skip tests if Ollama is not available."""
        if not check_ollama_available():
            pytest.skip("Ollama service not available")

    def test_simple_prompt_benchmark(self, benchmarker: ModelBenchmarker):
        """Benchmark models with simple prompts."""
        for model in benchmarker.models:
            if not benchmarker.check_model_available(model):
                pytest.skip(f"Model {model} not available")

            result = benchmarker.benchmark_model(model, "simple")

            assert result.success_rate > 0, f"All iterations failed for {model}"
            assert result.avg_llm_time > 0, "LLM time should be positive"

            logger.info(
                "simple_benchmark_complete",
                model=model,
                avg_time=result.avg_llm_time,
                tokens_per_sec=result.tokens_per_second,
            )

    def test_medium_prompt_benchmark(self, benchmarker: ModelBenchmarker):
        """Benchmark models with medium complexity prompts."""
        for model in benchmarker.models:
            if not benchmarker.check_model_available(model):
                pytest.skip(f"Model {model} not available")

            result = benchmarker.benchmark_model(model, "medium")

            assert result.success_rate > 0, f"All iterations failed for {model}"

            # Medium prompts should take longer than simple ones
            logger.info(
                "medium_benchmark_complete",
                model=model,
                avg_time=result.avg_llm_time,
                tokens_per_sec=result.tokens_per_second,
            )

    def test_complex_prompt_benchmark(self, benchmarker: ModelBenchmarker):
        """Benchmark models with complex prompts."""
        for model in benchmarker.models:
            if not benchmarker.check_model_available(model):
                pytest.skip(f"Model {model} not available")

            result = benchmarker.benchmark_model(model, "complex")

            assert result.success_rate > 0, f"All iterations failed for {model}"

            logger.info(
                "complex_benchmark_complete",
                model=model,
                avg_time=result.avg_llm_time,
                tokens_per_sec=result.tokens_per_second,
            )

    def test_code_generation_benchmark(self, benchmarker: ModelBenchmarker):
        """Benchmark models for code generation."""
        for model in benchmarker.models:
            if not benchmarker.check_model_available(model):
                pytest.skip(f"Model {model} not available")

            result = benchmarker.benchmark_model(model, "code")

            assert result.success_rate > 0, f"All iterations failed for {model}"

            logger.info(
                "code_benchmark_complete",
                model=model,
                avg_time=result.avg_llm_time,
                tokens_per_sec=result.tokens_per_second,
            )

    def test_benchmark_summary(self, benchmarker: ModelBenchmarker):
        """Print and save benchmark summary."""
        if not benchmarker.results:
            pytest.skip("No benchmark results available")

        benchmarker.print_summary()

        # Save results to file
        output_path = Path("tests/benchmark/results") / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        benchmarker.save_results(output_path)

        assert output_path.exists(), "Results file should be created"


def check_vector_store_ready() -> bool:
    """Check if vector store has documents indexed."""
    try:
        from app.rag.vector_store import get_vector_store
        store = get_vector_store()
        return store.count() > 0
    except Exception:
        return False


def check_configured_model_available() -> bool:
    """Check if the configured Ollama model is available."""
    try:
        settings = get_settings()
        configured_model = settings.ollama_model
        available = ollama.list()
        models_list = available.get("models", []) if isinstance(available, dict) else getattr(available, "models", [])
        model_names = []
        for m in models_list:
            name = m.get("name") if isinstance(m, dict) else getattr(m, "model", None)
            if name:
                model_names.append(name)
        # Check if configured model (or its base) is available
        base_model = configured_model.split(":")[0]
        return any(configured_model in name or base_model in name for name in model_names)
    except Exception:
        return False


@pytest.mark.benchmark
@pytest.mark.slow
class TestQAAgentBenchmark:
    """Benchmark tests for the QA Agent with RAG pipeline."""

    @pytest.fixture(autouse=True)
    def skip_if_not_ready(self):
        """Skip tests if Ollama, vector store, or configured model is not available."""
        if not check_ollama_available():
            pytest.skip("Ollama service not available")
        if not check_configured_model_available():
            pytest.skip("Configured Ollama model not available")
        if not check_vector_store_ready():
            pytest.skip("Vector store is empty - run indexing first")

    @pytest.fixture
    def qa_agent(self) -> QAAgent:
        """Create a QA agent for testing."""
        return QAAgent()

    def test_qa_agent_response_time(self, qa_agent: QAAgent, benchmark_iterations: int):
        """Benchmark QA agent response times."""
        question = "How do I configure the application?"

        times: list[float] = []
        llm_times: list[float] = []
        retrieval_times: list[float] = []

        for i in range(benchmark_iterations):
            try:
                result = qa_agent.answer(question, top_k=3, temperature=0.7, max_tokens=500)

                times.append(result["processing_time"])
                if "llm_duration" in result:
                    llm_times.append(result["llm_duration"])
                if "retrieval_time" in result:
                    retrieval_times.append(result["retrieval_time"])

                logger.info(
                    "qa_benchmark_iteration",
                    iteration=i + 1,
                    processing_time=result["processing_time"],
                    llm_duration=result.get("llm_duration"),
                    retrieval_time=result.get("retrieval_time"),
                    model=result.get("model"),
                )

            except Exception as e:
                logger.error("qa_benchmark_failed", iteration=i + 1, error=str(e))

        if times:
            avg_time = statistics.mean(times)
            avg_llm = statistics.mean(llm_times) if llm_times else 0
            avg_retrieval = statistics.mean(retrieval_times) if retrieval_times else 0

            logger.info(
                "qa_benchmark_summary",
                iterations=len(times),
                avg_total_time=round(avg_time, 3),
                avg_llm_time=round(avg_llm, 3),
                avg_retrieval_time=round(avg_retrieval, 3),
            )

            print(f"\nQA Agent Benchmark ({len(times)} iterations):")
            print(f"  Avg Total Time: {avg_time:.3f}s")
            print(f"  Avg LLM Time: {avg_llm:.3f}s")
            print(f"  Avg Retrieval Time: {avg_retrieval:.3f}s")

        assert len(times) > 0, "At least one iteration should succeed"

    def test_qa_agent_with_different_top_k(self, qa_agent: QAAgent):
        """Benchmark QA agent with different top_k values."""
        question = "What are the main features of this application?"

        top_k_values = [1, 3, 5, 10]
        results: dict[int, dict[str, float]] = {}

        for top_k in top_k_values:
            try:
                result = qa_agent.answer(question, top_k=top_k, temperature=0.7, max_tokens=500)

                results[top_k] = {
                    "processing_time": result["processing_time"],
                    "llm_duration": result.get("llm_duration", 0),
                    "retrieval_time": result.get("retrieval_time", 0),
                }

                logger.info(
                    "qa_top_k_benchmark",
                    top_k=top_k,
                    processing_time=result["processing_time"],
                    retrieval_time=result.get("retrieval_time"),
                )

            except Exception as e:
                logger.error("qa_top_k_benchmark_failed", top_k=top_k, error=str(e))

        if results:
            print("\nQA Agent Top-K Benchmark:")
            for k, data in sorted(results.items()):
                print(f"  top_k={k}: Total={data['processing_time']:.3f}s, LLM={data['llm_duration']:.3f}s, Retrieval={data['retrieval_time']:.3f}s")

        assert len(results) > 0, "At least one top_k test should succeed"


def check_model_available_for_test(models: list[str]) -> bool:
    """Check if any of the specified models are available."""
    try:
        available = ollama.list()
        models_list = available.get("models", []) if isinstance(available, dict) else getattr(available, "models", [])
        model_names = []
        for m in models_list:
            name = m.get("name") if isinstance(m, dict) else getattr(m, "model", None)
            if name:
                model_names.append(name)
        return any(any(model in name or name.startswith(model.split(":")[0]) for name in model_names) for model in models)
    except Exception:
        return False


@pytest.mark.benchmark
@pytest.mark.slow
class TestModelComparison:
    """Comparison tests across multiple models."""

    @pytest.fixture(autouse=True)
    def skip_if_not_ready(self, benchmark_models: list[str]):
        """Skip tests if Ollama or models are not available."""
        if not check_ollama_available():
            pytest.skip("Ollama service not available")
        if not check_model_available_for_test(benchmark_models):
            pytest.skip("No benchmark models available in Ollama")

    def test_compare_models(self, benchmark_models: list[str], benchmark_iterations: int):
        """Compare response times across different models."""
        prompt = "Explain what a REST API is in 2-3 sentences."

        results: dict[str, list[float]] = {}

        for model in benchmark_models:
            try:
                # Check if model is available
                available = ollama.list()
                # Handle both dict (older versions) and Pydantic model (newer versions)
                models_list = available.get("models", []) if isinstance(available, dict) else getattr(available, "models", [])
                model_names = []
                for m in models_list:
                    name = m.get("name") if isinstance(m, dict) else getattr(m, "model", None)
                    if name:
                        model_names.append(name)
                if not any(model in name for name in model_names):
                    logger.warning("model_not_available_for_comparison", model=model)
                    continue

                times = []
                for i in range(benchmark_iterations):
                    start = time.time()
                    ollama.chat(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        options={"temperature": 0.7, "num_predict": 100},
                    )
                    times.append(time.time() - start)

                results[model] = times

                logger.info(
                    "model_comparison_complete",
                    model=model,
                    avg_time=statistics.mean(times),
                    iterations=len(times),
                )

            except Exception as e:
                logger.error("model_comparison_failed", model=model, error=str(e))

        if results:
            print("\nModel Comparison Results:")
            print("-" * 50)
            for model, times in sorted(results.items(), key=lambda x: statistics.mean(x[1])):
                avg = statistics.mean(times)
                std = statistics.stdev(times) if len(times) > 1 else 0
                print(f"  {model}: {avg:.3f}s (±{std:.3f}s)")

        assert len(results) > 0, "At least one model comparison should succeed"


# Standalone benchmark runner
if __name__ == "__main__":
    """Run benchmarks directly without pytest."""
    models = get_benchmark_models()
    iterations = get_benchmark_iterations()

    print(f"Running benchmarks for models: {models}")
    print(f"Iterations per test: {iterations}")

    benchmarker = ModelBenchmarker(models=models, iterations=iterations)
    benchmarker.benchmark_all(prompt_types=["simple", "medium"])
    benchmarker.print_summary()

    output_path = Path("tests/benchmark/results") / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    benchmarker.save_results(output_path)
    print(f"\nResults saved to: {output_path}")

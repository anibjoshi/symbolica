"""Inference-related types for symbolic reasoning."""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict

# Import base types
from .base_types import Fact, Rule, Conclusion


@dataclass
class ConditionEvaluation:
    """Details about how a condition was evaluated."""
    condition_text: str
    fact_matched: Fact
    operator: str
    expected_value: Any
    actual_value: Any
    result: bool
    explanation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "condition_text": self.condition_text,
            "fact_matched": {
                "key": self.fact_matched.key,
                "value": self.fact_matched.value
            },
            "operator": self.operator,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "result": self.result,
            "explanation": self.explanation
        }


@dataclass
class InferenceStep:
    """A single step in the inference process.
    
    Represents one rule application during inference,
    including the rule used, facts matched, and conclusions drawn.
    """
    step_number: int
    rule_applied: Rule
    facts_matched: List[Fact]
    conclusions_drawn: List[Conclusion]
    condition_evaluations: List[ConditionEvaluation] = field(default_factory=list)
    reasoning_explanation: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: float = 0.0
    
    @property
    def success(self) -> bool:
        """Check if this step successfully drew conclusions."""
        return len(self.conclusions_drawn) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for JSON serialization."""
        return {
            "step_number": self.step_number,
            "rule_applied": {
                "id": self.rule_applied.id,
                "name": self.rule_applied.metadata.get("name", self.rule_applied.id),
                "priority": self.rule_applied.priority
            },
            "facts_matched": [
                {"key": f.key, "value": f.value} for f in self.facts_matched
            ],
            "conclusions_drawn": [
                {
                    "key": c.fact.key,
                    "value": c.fact.value,
                    "confidence": c.confidence,
                    "rule_id": c.rule_id,
                    "metadata": c.metadata
                } for c in self.conclusions_drawn
            ],
            "condition_evaluations": [ce.to_dict() for ce in self.condition_evaluations],
            "reasoning_explanation": self.reasoning_explanation,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "success": self.success
        }
    
    def get_explanation(self) -> str:
        """Get a human-readable explanation of this inference step."""
        if self.reasoning_explanation:
            return self.reasoning_explanation
        
        rule_name = self.rule_applied.metadata.get("name", self.rule_applied.id)
        explanation_parts = [
            f"Step {self.step_number}: Applied rule '{rule_name}'"
        ]
        
        if self.condition_evaluations:
            explanation_parts.append("Condition evaluations:")
            for eval in self.condition_evaluations:
                explanation_parts.append(f"  • {eval.explanation}")
        
        if self.conclusions_drawn:
            explanation_parts.append("Therefore concluded:")
            for conclusion in self.conclusions_drawn:
                explanation_parts.append(
                    f"  • {conclusion.fact.key} = {conclusion.fact.value} "
                    f"(confidence: {conclusion.confidence:.0%})"
                )
        
        return "\n".join(explanation_parts)


@dataclass
class ReasoningTrace:
    """Complete trace of the reasoning process.
    
    Provides a complete audit trail of the inference process,
    including all steps taken and final conclusions reached.
    """
    steps: List[InferenceStep]
    final_conclusions: List[Conclusion]
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_execution_time_ms: float = 0.0
    metadata: Optional[dict] = None
    
    def add_step(self, step: InferenceStep) -> None:
        """Add a step to the trace.
        
        Args:
            step: The inference step to add
        """
        self.steps.append(step)
    
    def finalize(self, conclusions: List[Conclusion]) -> None:
        """Finalize the trace with conclusions.
        
        Args:
            conclusions: Final conclusions from inference
        """
        self.final_conclusions = conclusions
        self.end_time = datetime.now()
        if self.start_time:
            self.total_execution_time_ms = (
                (self.end_time - self.start_time).total_seconds() * 1000
            )
    
    @property
    def total_rules_fired(self) -> int:
        """Get total number of rules fired during inference."""
        return len(self.steps)
    
    @property
    def total_conclusions_drawn(self) -> int:
        """Get total number of conclusions drawn across all steps."""
        return sum(len(step.conclusions_drawn) for step in self.steps)
    
    @property
    def average_step_time_ms(self) -> float:
        """Get average execution time per step."""
        if not self.steps:
            return 0.0
        return sum(step.execution_time_ms for step in self.steps) / len(self.steps)
    
    def get_rule_usage_stats(self) -> dict[str, int]:
        """Get statistics on rule usage during inference.
        
        Returns:
            Dictionary mapping rule IDs to number of times fired
        """
        usage = {}
        for step in self.steps:
            rule_id = step.rule_applied.id
            usage[rule_id] = usage.get(rule_id, 0) + 1
        return usage

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for JSON serialization."""
        return {
            "steps": [step.to_dict() for step in self.steps],
            "final_conclusions": [
                {
                    "key": c.fact.key,
                    "value": c.fact.value,
                    "confidence": c.confidence,
                    "rule_id": c.rule_id,
                    "metadata": c.metadata
                } for c in self.final_conclusions
            ],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_execution_time_ms": self.total_execution_time_ms,
            "total_rules_fired": self.total_rules_fired,
            "total_conclusions_drawn": self.total_conclusions_drawn,
            "average_step_time_ms": self.average_step_time_ms,
            "rule_usage_stats": self.get_rule_usage_stats(),
            "reasoning_summary": self.get_reasoning_summary(),
            "metadata": self.metadata
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert trace to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def get_reasoning_summary(self) -> str:
        """Get a human-readable summary of the reasoning process."""
        if not self.steps:
            return "No reasoning steps occurred."
        
        summary_parts = [
            f"Reasoning completed in {len(self.steps)} steps, "
            f"drawing {len(self.final_conclusions)} unique conclusions."
        ]
        
        # Summarize what happened
        rule_names = []
        for step in self.steps:
            rule_name = step.rule_applied.metadata.get("name", step.rule_applied.id)
            if rule_name not in rule_names:
                rule_names.append(rule_name)
        
        if rule_names:
            summary_parts.append(f"Rules applied: {', '.join(rule_names[:3])}")
            if len(rule_names) > 3:
                summary_parts[-1] += f" and {len(rule_names) - 3} others"
        
        return " ".join(summary_parts)
    
    def get_detailed_explanation(self) -> str:
        """Get a detailed step-by-step explanation of the reasoning."""
        if not self.steps:
            return "No reasoning occurred."
        
        explanation_parts = [
            f"Detailed Reasoning Trace ({len(self.steps)} steps):",
            "=" * 50
        ]
        
        for step in self.steps:
            explanation_parts.append(f"\n{step.get_explanation()}")
        
        if self.final_conclusions:
            explanation_parts.append(f"\nFinal Summary:")
            explanation_parts.append(f"Drew {len(self.final_conclusions)} conclusions:")
            for conclusion in self.final_conclusions:
                explanation_parts.append(
                    f"  • {conclusion.fact.key} = {conclusion.fact.value} "
                    f"(from {conclusion.rule_id})"
                )
        
        return "\n".join(explanation_parts)


@dataclass
class InferenceResult:
    """Result of running inference.
    
    Contains the final conclusions, reasoning trace, and
    performance metrics from an inference run.
    """
    conclusions: List[Conclusion]
    trace: ReasoningTrace
    execution_time_ms: float
    facts_processed: int
    rules_fired: int
    
    @property
    def success(self) -> bool:
        """Check if inference produced any conclusions."""
        return len(self.conclusions) > 0
    
    @property
    def unique_conclusions(self) -> List[Conclusion]:
        """Get unique conclusions (deduplicated by fact key-value)."""
        seen = set()
        unique = []
        for conclusion in self.conclusions:
            key = (conclusion.fact.key, str(conclusion.fact.value))
            if key not in seen:
                seen.add(key)
                unique.append(conclusion)
        return unique
    
    @property
    def confidence_distribution(self) -> dict[float, int]:
        """Get distribution of confidence values in conclusions."""
        distribution = {}
        for conclusion in self.conclusions:
            conf = conclusion.confidence
            distribution[conf] = distribution.get(conf, 0) + 1
        return distribution
    
    def get_conclusions_by_rule(self) -> dict[str, List[Conclusion]]:
        """Group conclusions by the rule that generated them.
        
        Returns:
            Dictionary mapping rule IDs to their conclusions
        """
        by_rule = {}
        for conclusion in self.conclusions:
            rule_id = conclusion.rule_id
            if rule_id not in by_rule:
                by_rule[rule_id] = []
            by_rule[rule_id].append(conclusion)
        return by_rule
    
    def get_performance_summary(self) -> dict[str, any]:
        """Get a summary of performance metrics.
        
        Returns:
            Dictionary with key performance indicators
        """
        return {
            "total_execution_time_ms": self.execution_time_ms,
            "facts_processed": self.facts_processed,
            "rules_fired": self.rules_fired,
            "conclusions_drawn": len(self.conclusions),
            "unique_conclusions": len(self.unique_conclusions),
            "avg_time_per_rule_ms": self.execution_time_ms / self.rules_fired if self.rules_fired > 0 else 0,
            "conclusions_per_rule": len(self.conclusions) / self.rules_fired if self.rules_fired > 0 else 0,
            "inference_rate_rules_per_second": self.rules_fired / (self.execution_time_ms / 1000) if self.execution_time_ms > 0 else 0
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization.
        
        This is the primary method for LLMs to get structured output from Symbolica.
        """
        return {
            "success": self.success,
            "conclusions": [
                {
                    "key": c.fact.key,
                    "value": c.fact.value,
                    "confidence": c.confidence,
                    "rule_id": c.rule_id,
                    "rule_name": c.metadata.get("name", c.rule_id),
                    "metadata": c.metadata
                } for c in self.conclusions
            ],
            "unique_conclusions": [
                {
                    "key": c.fact.key,
                    "value": c.fact.value,
                    "confidence": c.confidence,
                    "rule_id": c.rule_id,
                    "rule_name": c.metadata.get("name", c.rule_id),
                    "metadata": c.metadata
                } for c in self.unique_conclusions
            ],
            "reasoning_trace": {
                "summary": self.trace.get_reasoning_summary(),
                "detailed_explanation": self.trace.get_detailed_explanation(),
                "steps": [step.to_dict() for step in self.trace.steps],
                "total_steps": len(self.trace.steps),
                "execution_time_ms": self.trace.total_execution_time_ms
            },
            "performance": self.get_performance_summary(),
            "trace": self.trace.to_dict() if self.trace else None
        }

    def to_json(self, indent: int = 2, include_trace: bool = True) -> str:
        """Convert result to JSON string.
        
        Args:
            indent: JSON indentation level
            include_trace: Whether to include the full reasoning trace
            
        Returns:
            JSON string representation of the inference result
        """
        data = self.to_dict()
        if not include_trace:
            data.pop("trace", None)
        
        return json.dumps(data, indent=indent, default=str) 
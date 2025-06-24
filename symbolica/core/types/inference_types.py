"""Inference-related types for symbolic reasoning."""

from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field

# Import base types
from .base_types import Fact, Rule, Conclusion


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
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: float = 0.0
    
    @property
    def success(self) -> bool:
        """Check if this step successfully drew conclusions."""
        return len(self.conclusions_drawn) > 0


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
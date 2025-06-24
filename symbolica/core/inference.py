"""Inference engine that orchestrates reasoning and generates explanations."""

import time
from datetime import datetime
from typing import Iterator, List, Optional, Dict, Any

from .types import (
    InferenceResult,
    ReasoningTrace,
    InferenceStep,
    Conclusion,
    Fact
)
from .fact_store import FactStore
from .rule_engine import RuleEngine


class Inference:
    """Orchestrates reasoning process and generates explanations."""
    
    def __init__(self, engine: RuleEngine):
        """Initialize the inference orchestrator.
        
        Args:
            engine: The rule engine to use for inference
        """
        self.engine = engine
        self.last_trace: Optional[ReasoningTrace] = None
        self.last_result: Optional[InferenceResult] = None
        
    def run(
        self, 
        facts: FactStore, 
        max_iterations: int = 100,
        timeout_seconds: Optional[float] = None
    ) -> InferenceResult:
        """Run inference on the fact store.
        
        Args:
            facts: The fact store containing initial facts
            max_iterations: Maximum number of inference iterations
            timeout_seconds: Optional timeout in seconds
            
        Returns:
            InferenceResult containing conclusions and trace
        """
        start_time = time.time()
        initial_fact_count = len(facts)
        
        # Run inference with tracing
        conclusions, trace = self.engine.evaluate_with_trace(facts, max_iterations)
        
        end_time = time.time()
        execution_time_ms = (end_time - start_time) * 1000
        
        # Check for timeout
        if timeout_seconds and (end_time - start_time) > timeout_seconds:
            trace.metadata = trace.metadata or {}
            trace.metadata["timeout"] = True
            trace.metadata["timeout_seconds"] = timeout_seconds
        
        # Create result
        result = InferenceResult(
            conclusions=conclusions,
            trace=trace,
            execution_time_ms=execution_time_ms,
            facts_processed=len(facts),
            rules_fired=len(trace.steps)
        )
        
        # Store for later access
        self.last_trace = trace
        self.last_result = result
        
        return result
    
    def step_by_step(
        self, 
        facts: FactStore, 
        max_iterations: int = 100
    ) -> Iterator[InferenceStep]:
        """Run inference step by step, yielding each inference step.
        
        Args:
            facts: The fact store containing initial facts
            max_iterations: Maximum number of inference iterations
            
        Yields:
            Each inference step as it occurs
        """
        all_facts = facts.get_all_facts()
        iteration = 0
        step_number = 0
        
        trace = ReasoningTrace(steps=[], final_conclusions=[])
        
        while iteration < max_iterations:
            iteration += 1
            step_occurred = False
            
            # Evaluate rules in priority order
            for rule in self.engine._priority_sorted_rules:
                if not rule.enabled:
                    continue
                
                start_time = time.time()
                
                if rule.can_fire(all_facts):
                    rule_conclusions = self.engine._evaluate_single_rule(rule, all_facts)
                    
                    if rule_conclusions:
                        step_number += 1
                        step_occurred = True
                        
                        # Find matching facts
                        matching_facts = []
                        for condition in rule.conditions:
                            condition_matches = [f for f in all_facts if condition.evaluate(f)]
                            matching_facts.extend(condition_matches)
                        
                        # Remove duplicates
                        seen = set()
                        unique_matching_facts = []
                        for fact in matching_facts:
                            fact_id = (fact.key, fact.timestamp)
                            if fact_id not in seen:
                                seen.add(fact_id)
                                unique_matching_facts.append(fact)
                        
                        execution_time = (time.time() - start_time) * 1000
                        
                        step = InferenceStep(
                            step_number=step_number,
                            rule_applied=rule,
                            facts_matched=unique_matching_facts,
                            conclusions_drawn=rule_conclusions,
                            execution_time_ms=execution_time
                        )
                        
                        trace.add_step(step)
                        
                        # Add new facts from conclusions
                        for conclusion in rule_conclusions:
                            facts.add(
                                conclusion.fact.key,
                                conclusion.fact.value,
                                conclusion.fact.metadata
                            )
                            all_facts.append(conclusion.fact)
                        
                        yield step
            
            if not step_occurred:
                break
        
        # Finalize trace
        all_conclusions = []
        for step in trace.steps:
            all_conclusions.extend(step.conclusions_drawn)
        
        trace.finalize(all_conclusions)
        self.last_trace = trace
    
    def explain_conclusion(self, conclusion: Conclusion, facts: FactStore) -> str:
        """Generate a natural language explanation for a conclusion.
        
        Args:
            conclusion: The conclusion to explain
            facts: The fact store used for inference
            
        Returns:
            Natural language explanation
        """
        rule = self.engine.get_rule(conclusion.rule_id)
        if not rule:
            return f"Conclusion '{conclusion.fact.key}={conclusion.fact.value}' was derived by unknown rule."
        
        explanation_parts = []
        
        # Start with the conclusion
        explanation_parts.append(
            f"Concluded that '{conclusion.fact.key}' = '{conclusion.fact.value}' "
            f"(confidence: {conclusion.confidence:.2f})"
        )
        
        # Explain the rule
        explanation_parts.append(f"This was derived using rule '{rule.id}':")
        
        # Explain conditions
        condition_explanations = []
        for i, condition in enumerate(rule.conditions):
            condition_explanations.append(
                f"  {i+1}. {condition.field} {condition.operator.value} {condition.value}"
            )
        
        if condition_explanations:
            explanation_parts.append("The rule conditions were:")
            explanation_parts.extend(condition_explanations)
        
        # Explain supporting facts
        if conclusion.supporting_facts:
            explanation_parts.append("This was supported by the following facts:")
            for i, fact in enumerate(conclusion.supporting_facts):
                explanation_parts.append(
                    f"  {i+1}. {fact.key} = {fact.value} (confidence: {fact.confidence:.2f})"
                )
        
        return "\n".join(explanation_parts)
    
    def get_trace(self) -> Optional[ReasoningTrace]:
        """Get the last reasoning trace.
        
        Returns:
            The last reasoning trace or None if no inference has been run
        """
        return self.last_trace
    
    def get_last_result(self) -> Optional[InferenceResult]:
        """Get the last inference result.
        
        Returns:
            The last inference result or None if no inference has been run
        """
        return self.last_result
    
    def explain_trace(self, trace: Optional[ReasoningTrace] = None) -> str:
        """Generate a natural language explanation of the reasoning trace.
        
        Args:
            trace: Optional trace to explain (uses last trace if None)
            
        Returns:
            Natural language explanation of the reasoning process
        """
        if trace is None:
            trace = self.last_trace
        
        if not trace:
            return "No reasoning trace available."
        
        explanation_parts = []
        
        # Summary
        explanation_parts.append(
            f"Reasoning completed in {len(trace.steps)} steps, "
            f"producing {len(trace.final_conclusions)} conclusions."
        )
        
        if trace.total_execution_time_ms > 0:
            explanation_parts.append(
                f"Total execution time: {trace.total_execution_time_ms:.2f}ms"
            )
        
        explanation_parts.append("")  # Empty line
        
        # Explain each step
        for step in trace.steps:
            explanation_parts.append(f"Step {step.step_number}:")
            explanation_parts.append(f"  Applied rule: {step.rule_applied.id}")
            
            if step.facts_matched:
                explanation_parts.append("  Matched facts:")
                for fact in step.facts_matched:
                    explanation_parts.append(f"    - {fact.key} = {fact.value}")
            
            if step.conclusions_drawn:
                explanation_parts.append("  Drew conclusions:")
                for conclusion in step.conclusions_drawn:
                    explanation_parts.append(
                        f"    - {conclusion.fact.key} = {conclusion.fact.value} "
                        f"(confidence: {conclusion.confidence:.2f})"
                    )
            
            if step.execution_time_ms > 0:
                explanation_parts.append(f"  Execution time: {step.execution_time_ms:.2f}ms")
            
            explanation_parts.append("")  # Empty line between steps
        
        # Final conclusions summary
        if trace.final_conclusions:
            explanation_parts.append("Final conclusions:")
            for conclusion in trace.final_conclusions:
                explanation_parts.append(
                    f"  - {conclusion.fact.key} = {conclusion.fact.value} "
                    f"(confidence: {conclusion.confidence:.2f}, from rule: {conclusion.rule_id})"
                )
        
        return "\n".join(explanation_parts)
    
    def analyze_performance(self, trace: Optional[ReasoningTrace] = None) -> Dict[str, Any]:
        """Analyze the performance of the last inference run.
        
        Args:
            trace: Optional trace to analyze (uses last trace if None)
            
        Returns:
            Dictionary containing performance metrics
        """
        if trace is None:
            trace = self.last_trace
        
        if not trace:
            return {"error": "No trace available for analysis"}
        
        # Basic metrics
        total_steps = len(trace.steps)
        total_time = trace.total_execution_time_ms
        total_conclusions = len(trace.final_conclusions)
        
        # Rule usage statistics
        rule_usage = {}
        step_times = []
        
        for step in trace.steps:
            rule_id = step.rule_applied.id
            rule_usage[rule_id] = rule_usage.get(rule_id, 0) + 1
            step_times.append(step.execution_time_ms)
        
        # Time statistics
        avg_step_time = sum(step_times) / len(step_times) if step_times else 0
        max_step_time = max(step_times) if step_times else 0
        min_step_time = min(step_times) if step_times else 0
        
        return {
            "total_steps": total_steps,
            "total_execution_time_ms": total_time,
            "total_conclusions": total_conclusions,
            "avg_step_time_ms": avg_step_time,
            "max_step_time_ms": max_step_time,
            "min_step_time_ms": min_step_time,
            "rule_usage": rule_usage,
            "most_used_rule": max(rule_usage.items(), key=lambda x: x[1])[0] if rule_usage else None,
            "conclusions_per_step": total_conclusions / total_steps if total_steps > 0 else 0,
            "throughput_steps_per_second": total_steps / (total_time / 1000) if total_time > 0 else 0
        }
    
    def debug_step(self, step_number: int, trace: Optional[ReasoningTrace] = None) -> Dict[str, Any]:
        """Get detailed debug information for a specific step.
        
        Args:
            step_number: The step number to debug (1-indexed)
            trace: Optional trace to use (uses last trace if None)
            
        Returns:
            Dictionary with detailed step information
        """
        if trace is None:
            trace = self.last_trace
        
        if not trace or step_number < 1 or step_number > len(trace.steps):
            return {"error": f"Invalid step number: {step_number}"}
        
        step = trace.steps[step_number - 1]  # Convert to 0-indexed
        
        return {
            "step_number": step.step_number,
            "rule_id": step.rule_applied.id,
            "rule_priority": step.rule_applied.priority,
            "rule_enabled": step.rule_applied.enabled,
            "conditions": [
                {
                    "field": cond.field,
                    "operator": cond.operator.value,
                    "value": cond.value
                }
                for cond in step.rule_applied.conditions
            ],
            "matched_facts": [
                {
                    "key": fact.key,
                    "value": fact.value,
                    "confidence": fact.confidence,
                    "timestamp": fact.timestamp.isoformat()
                }
                for fact in step.facts_matched
            ],
            "conclusions_drawn": [
                {
                    "fact_key": conclusion.fact.key,
                    "fact_value": conclusion.fact.value,
                    "confidence": conclusion.confidence,
                    "rule_id": conclusion.rule_id
                }
                for conclusion in step.conclusions_drawn
            ],
            "execution_time_ms": step.execution_time_ms,
            "timestamp": step.timestamp.isoformat()
        }
    
    def validate_inference_state(self, facts: FactStore) -> List[str]:
        """Validate the current state for potential inference issues.
        
        Args:
            facts: The fact store to validate
            
        Returns:
            List of validation warnings/issues
        """
        issues = []
        
        # Check if there are any facts
        if len(facts) == 0:
            issues.append("No facts available for inference")
        
        # Check if there are any enabled rules
        enabled_rules = [r for r in self.engine.rules if r.enabled]
        if not enabled_rules:
            issues.append("No enabled rules available for inference")
        
        # Check for rules that can never fire
        all_facts = facts.get_all_facts()
        applicable_rules = self.engine.get_applicable_rules(all_facts)
        if not applicable_rules:
            issues.append("No rules are applicable to the current facts")
        
        # Check for circular dependencies (simplified check)
        rule_dependencies = {}
        for rule in self.engine.rules:
            dependencies = set()
            for condition in rule.conditions:
                dependencies.add(condition.field)
            rule_dependencies[rule.id] = dependencies
        
        # Check rule validation errors
        validation_errors = self.engine.validate_rules()
        if validation_errors:
            issues.append(f"Found {len(validation_errors)} rule validation errors")
        
        return issues
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Inference(engine={repr(self.engine)})" 
"""LLM Bridge for converting symbolic reasoning to natural language."""

import json
from typing import Any, Dict, List, Optional, Union

from ..core.types import Conclusion, ReasoningTrace, Rule, Fact
from ..core.fact_store import FactStore


class LLMBridge:
    """Converts symbolic outputs to natural language explanations."""
    
    def __init__(self, llm_client: Any = None, model_name: str = "gpt-3.5-turbo"):
        """Initialize the LLM bridge.
        
        Args:
            llm_client: LLM client (OpenAI, Anthropic, etc.)
            model_name: Name of the model to use
        """
        self.llm_client = llm_client
        self.model_name = model_name
        self._default_templates = self._load_default_templates()
    
    def explain_conclusion(self, conclusion: Conclusion, context: Optional[str] = None) -> str:
        """Generate natural language explanation for a conclusion.
        
        Args:
            conclusion: The conclusion to explain
            context: Optional context information
            
        Returns:
            Natural language explanation
        """
        if self.llm_client is None:
            return self._fallback_explain_conclusion(conclusion)
        
        prompt = self._build_conclusion_prompt(conclusion, context)
        
        try:
            response = self._call_llm(prompt)
            return response.strip()
        except Exception as e:
            # Fallback to template-based explanation
            return self._fallback_explain_conclusion(conclusion)
    
    def explain_trace(self, trace: ReasoningTrace, context: Optional[str] = None) -> str:
        """Generate natural language explanation of reasoning trace.
        
        Args:
            trace: The reasoning trace to explain
            context: Optional context information
            
        Returns:
            Natural language explanation of the reasoning process
        """
        if self.llm_client is None:
            return self._fallback_explain_trace(trace)
        
        prompt = self._build_trace_prompt(trace, context)
        
        try:
            response = self._call_llm(prompt)
            return response.strip()
        except Exception as e:
            return self._fallback_explain_trace(trace)
    
    def suggest_rules(self, facts: FactStore, logs: List[str], domain: Optional[str] = None) -> List[Rule]:
        """Suggest rules based on facts and system logs.
        
        Args:
            facts: Current fact store
            logs: System logs or error messages
            domain: Optional domain context
            
        Returns:
            List of suggested rules
        """
        if self.llm_client is None:
            return []
        
        prompt = self._build_rule_suggestion_prompt(facts, logs, domain)
        
        try:
            response = self._call_llm(prompt)
            return self._parse_suggested_rules(response)
        except Exception as e:
            return []
    
    def summarize_facts(self, facts: FactStore, max_facts: int = 50) -> str:
        """Generate a natural language summary of facts.
        
        Args:
            facts: The fact store to summarize
            max_facts: Maximum number of facts to include
            
        Returns:
            Natural language summary
        """
        all_facts = facts.get_all_facts()
        if not all_facts:
            return "No facts available in the store."
        
        # Take most recent facts up to the limit
        recent_facts = sorted(all_facts, key=lambda f: f.timestamp, reverse=True)[:max_facts]
        
        if self.llm_client is None:
            return self._fallback_summarize_facts(recent_facts)
        
        prompt = self._build_fact_summary_prompt(recent_facts)
        
        try:
            response = self._call_llm(prompt)
            return response.strip()
        except Exception as e:
            return self._fallback_summarize_facts(recent_facts)
    
    def _build_conclusion_prompt(self, conclusion: Conclusion, context: Optional[str] = None) -> str:
        """Build prompt for explaining a conclusion."""
        prompt_parts = [
            "Explain the following logical conclusion in clear, natural language:",
            "",
            f"Conclusion: {conclusion.fact.key} = {conclusion.fact.value}",
            f"Confidence: {conclusion.confidence:.2f}",
            f"Derived by rule: {conclusion.rule_id}",
        ]
        
        if conclusion.supporting_facts:
            prompt_parts.extend([
                "",
                "Supporting facts:"
            ])
            for i, fact in enumerate(conclusion.supporting_facts):
                prompt_parts.append(f"{i+1}. {fact.key} = {fact.value}")
        
        if context:
            prompt_parts.extend([
                "",
                f"Context: {context}"
            ])
        
        prompt_parts.extend([
            "",
            "Please provide a clear explanation of why this conclusion was reached.",
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_trace_prompt(self, trace: ReasoningTrace, context: Optional[str] = None) -> str:
        """Build prompt for explaining a reasoning trace."""
        prompt_parts = [
            "Explain the following logical reasoning process in clear, natural language:",
            "",
            f"The reasoning process completed in {len(trace.steps)} steps and produced {len(trace.final_conclusions)} conclusions.",
        ]
        
        if trace.total_execution_time_ms > 0:
            prompt_parts.append(f"Execution time: {trace.total_execution_time_ms:.2f}ms")
        
        prompt_parts.extend([
            "",
            "Reasoning steps:"
        ])
        
        for step in trace.steps:
            prompt_parts.extend([
                f"Step {step.step_number}: Applied rule '{step.rule_applied.id}'",
                f"  Matched facts: {len(step.facts_matched)}",
                f"  Drew conclusions: {len(step.conclusions_drawn)}"
            ])
        
        if trace.final_conclusions:
            prompt_parts.extend([
                "",
                "Final conclusions:"
            ])
            for conclusion in trace.final_conclusions:
                prompt_parts.append(f"- {conclusion.fact.key} = {conclusion.fact.value}")
        
        if context:
            prompt_parts.extend([
                "",
                f"Context: {context}"
            ])
        
        prompt_parts.extend([
            "",
            "Please provide a narrative explanation of this reasoning process.",
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_rule_suggestion_prompt(self, facts: FactStore, logs: List[str], domain: Optional[str] = None) -> str:
        """Build prompt for suggesting rules."""
        prompt_parts = [
            "Based on the following facts and system logs, suggest logical rules that could help with automated reasoning:",
            "",
            "Current facts:"
        ]
        
        # Include sample facts
        all_facts = facts.get_all_facts()[:20]  # Limit to avoid long prompts
        for fact in all_facts:
            prompt_parts.append(f"- {fact.key} = {fact.value}")
        
        if logs:
            prompt_parts.extend([
                "",
                "System logs:"
            ])
            for log in logs[:10]:  # Limit logs
                prompt_parts.append(f"- {log}")
        
        if domain:
            prompt_parts.extend([
                "",
                f"Domain: {domain}"
            ])
        
        prompt_parts.extend([
            "",
            "Please suggest rules in the following JSON format:",
            "{",
            '  "rules": [',
            '    {',
            '      "id": "rule_id",',
            '      "description": "Human readable description",',
            '      "conditions": [',
            '        {"field": "field_name", "operator": "==", "value": "expected_value"}',
            '      ],',
            '      "conclusions": [',
            '        {"fact_key": "new_fact", "fact_value": "derived_value", "confidence": 0.9}',
            '      ]',
            '    }',
            '  ]',
            '}'
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_fact_summary_prompt(self, facts: List[Fact]) -> str:
        """Build prompt for summarizing facts."""
        prompt_parts = [
            "Summarize the following facts in natural language:",
            ""
        ]
        
        for fact in facts:
            prompt_parts.append(f"- {fact.key} = {fact.value}")
        
        prompt_parts.extend([
            "",
            "Please provide a concise summary that captures the key information."
        ])
        
        return "\n".join(prompt_parts)
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt."""
        if hasattr(self.llm_client, 'chat'):
            # OpenAI-style client
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            return response.choices[0].message.content
        elif hasattr(self.llm_client, 'messages'):
            # Anthropic-style client
            response = self.llm_client.messages.create(
                model=self.model_name,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        else:
            # Generic client - assume it has a generate method
            return self.llm_client.generate(prompt)
    
    def _parse_suggested_rules(self, response: str) -> List[Rule]:
        """Parse LLM response into Rule objects."""
        try:
            data = json.loads(response)
            rules = []
            
            for rule_data in data.get("rules", []):
                from ..core.types import Condition, OperatorType, Conclusion
                
                conditions = []
                for cond_data in rule_data.get("conditions", []):
                    conditions.append(Condition(
                        field=cond_data["field"],
                        operator=OperatorType(cond_data["operator"]),
                        value=cond_data["value"]
                    ))
                
                conclusions = []
                for concl_data in rule_data.get("conclusions", []):
                    fact = Fact(
                        key=concl_data["fact_key"],
                        value=concl_data["fact_value"]
                    )
                    conclusions.append(Conclusion(
                        fact=fact,
                        confidence=concl_data.get("confidence", 1.0),
                        rule_id=rule_data["id"]
                    ))
                
                rule = Rule(
                    id=rule_data["id"],
                    conditions=conditions,
                    conclusions=conclusions,
                    metadata={"description": rule_data.get("description", "")}
                )
                rules.append(rule)
            
            return rules
        except (json.JSONDecodeError, KeyError, ValueError):
            return []
    
    def _fallback_explain_conclusion(self, conclusion: Conclusion) -> str:
        """Fallback explanation using templates."""
        template = self._default_templates["conclusion"]
        return template.format(
            fact_key=conclusion.fact.key,
            fact_value=conclusion.fact.value,
            confidence=conclusion.confidence,
            rule_id=conclusion.rule_id,
            num_supporting=len(conclusion.supporting_facts)
        )
    
    def _fallback_explain_trace(self, trace: ReasoningTrace) -> str:
        """Fallback trace explanation using templates."""
        template = self._default_templates["trace"]
        return template.format(
            num_steps=len(trace.steps),
            num_conclusions=len(trace.final_conclusions),
            execution_time=trace.total_execution_time_ms
        )
    
    def _fallback_summarize_facts(self, facts: List[Fact]) -> str:
        """Fallback fact summary using templates."""
        if not facts:
            return "No facts to summarize."
        
        summary_parts = [f"Summary of {len(facts)} facts:"]
        
        # Group by key
        fact_groups = {}
        for fact in facts:
            if fact.key not in fact_groups:
                fact_groups[fact.key] = []
            fact_groups[fact.key].append(fact)
        
        for key, key_facts in fact_groups.items():
            if len(key_facts) == 1:
                summary_parts.append(f"- {key}: {key_facts[0].value}")
            else:
                values = [str(f.value) for f in key_facts]
                summary_parts.append(f"- {key}: {len(values)} values ({', '.join(values[:3])}{'...' if len(values) > 3 else ''})")
        
        return "\n".join(summary_parts)
    
    def _load_default_templates(self) -> Dict[str, str]:
        """Load default explanation templates."""
        return {
            "conclusion": (
                "Based on the available evidence, I concluded that '{fact_key}' has the value '{fact_value}' "
                "with {confidence:.0%} confidence. This conclusion was derived using rule '{rule_id}' "
                "and is supported by {num_supporting} fact(s)."
            ),
            "trace": (
                "The reasoning process completed successfully in {num_steps} step(s), "
                "taking {execution_time:.2f}ms to execute. "
                "This process resulted in {num_conclusions} new conclusion(s)."
            )
        }
    
    def set_llm_client(self, client: Any, model_name: str = None) -> None:
        """Set or update the LLM client.
        
        Args:
            client: New LLM client
            model_name: Optional new model name
        """
        self.llm_client = client
        if model_name:
            self.model_name = model_name
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get information about the current LLM client."""
        return {
            "has_client": self.llm_client is not None,
            "model_name": self.model_name,
            "client_type": type(self.llm_client).__name__ if self.llm_client else None
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return f"LLMBridge(model={self.model_name}, has_client={self.llm_client is not None})" 
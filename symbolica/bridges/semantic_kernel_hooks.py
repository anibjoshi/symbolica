"""Semantic Kernel integration hooks for Symbolica."""

from typing import Any, Dict, List, Optional

try:
    from semantic_kernel import Kernel
    from semantic_kernel.plugin_definition import sk_function, sk_function_context_parameter
    from semantic_kernel.orchestration.sk_context import SKContext
    SEMANTIC_KERNEL_AVAILABLE = True
except ImportError:
    SEMANTIC_KERNEL_AVAILABLE = False
    # Define minimal types for graceful degradation
    def sk_function(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    def sk_function_context_parameter(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

import json
from ..core.fact_store import FactStore
from ..core.rule_engine import RuleEngine
from ..core.inference import Inference
from ..core.types import Fact, Rule, Conclusion
from .llm_bridge import LLMBridge


class SymbolicaPlugin:
    """Semantic Kernel plugin for symbolic reasoning."""
    
    def __init__(
        self,
        rule_engine: RuleEngine,
        llm_bridge: Optional[LLMBridge] = None,
        fact_store: Optional[FactStore] = None
    ):
        """Initialize the Symbolica plugin.
        
        Args:
            rule_engine: The rule engine to use
            llm_bridge: Optional LLM bridge for explanations
            fact_store: Optional pre-populated fact store
        """
        if not SEMANTIC_KERNEL_AVAILABLE:
            raise ImportError("Semantic Kernel is not available. Install with: pip install semantic-kernel")
        
        self.rule_engine = rule_engine
        self.llm_bridge = llm_bridge
        self.fact_store = fact_store or FactStore()
        self.inference = Inference(rule_engine)
    
    @sk_function(
        description="Add a fact to the symbolic reasoning system",
        name="add_fact"
    )
    @sk_function_context_parameter(
        name="key",
        description="The fact key/name"
    )
    @sk_function_context_parameter(
        name="value", 
        description="The fact value"
    )
    @sk_function_context_parameter(
        name="metadata",
        description="Optional metadata as JSON string",
        default_value="{}"
    )
    def add_fact(self, context: "SKContext") -> str:
        """Add a fact to the fact store."""
        key = context["key"]
        value = context["value"]
        metadata_str = context.get("metadata", "{}")
        
        try:
            metadata = json.loads(metadata_str) if metadata_str else {}
        except json.JSONDecodeError:
            metadata = {}
        
        fact = self.fact_store.add(key, value, metadata)
        return f"Added fact: {key} = {value}"
    
    @sk_function(
        description="Run symbolic inference on the current facts",
        name="run_inference"
    )
    @sk_function_context_parameter(
        name="max_iterations",
        description="Maximum number of inference iterations",
        default_value="100"
    )
    def run_inference(self, context: "SKContext") -> str:
        """Run inference and return results."""
        max_iterations = int(context.get("max_iterations", 100))
        
        result = self.inference.run(self.fact_store, max_iterations)
        
        if not result.conclusions:
            return "No conclusions were drawn from the available facts."
        
        # Format results
        lines = [f"Inference completed with {len(result.conclusions)} conclusions:"]
        
        for i, conclusion in enumerate(result.conclusions, 1):
            lines.append(
                f"{i}. {conclusion.fact.key} = {conclusion.fact.value} "
                f"(confidence: {conclusion.confidence:.2f}, rule: {conclusion.rule_id})"
            )
        
        if result.trace and result.trace.total_execution_time_ms > 0:
            lines.append(f"\nExecution time: {result.trace.total_execution_time_ms:.2f}ms")
        
        return "\n".join(lines)
    
    @sk_function(
        description="Get explanation for the last inference run",
        name="explain_reasoning"
    )
    def explain_reasoning(self, context: "SKContext") -> str:
        """Get natural language explanation of reasoning."""
        if not self.inference.last_trace:
            return "No reasoning trace available. Run inference first."
        
        if self.llm_bridge:
            return self.llm_bridge.explain_trace(self.inference.last_trace)
        else:
            return self.inference.explain_trace(self.inference.last_trace)
    
    @sk_function(
        description="Query facts from the fact store",
        name="query_facts"
    )
    @sk_function_context_parameter(
        name="pattern",
        description="Query pattern (e.g., 'key:pattern', 'value:pattern', '*pattern*')"
    )
    def query_facts(self, context: "SKContext") -> str:
        """Query facts using a pattern."""
        pattern = context["pattern"]
        facts = self.fact_store.query(pattern)
        
        if not facts:
            return f"No facts found matching pattern: {pattern}"
        
        lines = [f"Found {len(facts)} facts matching '{pattern}':"]
        for fact in facts:
            lines.append(f"- {fact.key} = {fact.value}")
        
        return "\n".join(lines)
    
    @sk_function(
        description="Get summary of all facts in the store",
        name="summarize_facts"
    )
    @sk_function_context_parameter(
        name="max_facts",
        description="Maximum number of facts to include in summary",
        default_value="20"
    )
    def summarize_facts(self, context: "SKContext") -> str:
        """Get a summary of facts."""
        max_facts = int(context.get("max_facts", 20))
        
        if self.llm_bridge:
            return self.llm_bridge.summarize_facts(self.fact_store, max_facts)
        else:
            facts = self.fact_store.get_all_facts()[:max_facts]
            if not facts:
                return "No facts available."
            
            lines = [f"Summary of {len(facts)} facts:"]
            for fact in facts:
                lines.append(f"- {fact.key}: {fact.value}")
            
            return "\n".join(lines)
    
    @sk_function(
        description="Add multiple facts from a JSON string",
        name="add_facts_json"
    )
    @sk_function_context_parameter(
        name="facts_json",
        description="JSON string containing facts as key-value pairs"
    )
    def add_facts_json(self, context: "SKContext") -> str:
        """Add multiple facts from JSON."""
        facts_json = context["facts_json"]
        
        try:
            facts_dict = json.loads(facts_json)
            added_count = 0
            
            for key, value in facts_dict.items():
                self.fact_store.add(key, value, {"source": "semantic_kernel_json"})
                added_count += 1
            
            return f"Added {added_count} facts from JSON input"
            
        except json.JSONDecodeError as e:
            return f"Invalid JSON format: {str(e)}"
    
    @sk_function(
        description="Clear all facts from the fact store",
        name="clear_facts"
    )
    def clear_facts(self, context: "SKContext") -> str:
        """Clear all facts."""
        fact_count = len(self.fact_store)
        self.fact_store.clear()
        return f"Cleared {fact_count} facts from the store"
    
    @sk_function(
        description="Get statistics about the reasoning engine",
        name="get_statistics"
    )
    def get_statistics(self, context: "SKContext") -> str:
        """Get engine statistics."""
        stats = self.rule_engine.get_statistics()
        fact_count = len(self.fact_store)
        
        lines = [
            "Symbolic Reasoning Engine Statistics:",
            f"- Total rules: {stats['total_rules']}",
            f"- Enabled rules: {stats['enabled_rules']}",
            f"- Disabled rules: {stats['disabled_rules']}",
            f"- Facts in store: {fact_count}",
            f"- Backend: {stats['backend']}"
        ]
        
        if stats.get('validation_errors', 0) > 0:
            lines.append(f"- Validation errors: {stats['validation_errors']}")
        
        return "\n".join(lines)
    
    @sk_function(
        description="Validate all rules in the engine",
        name="validate_rules"
    )
    def validate_rules(self, context: "SKContext") -> str:
        """Validate rules and return any errors."""
        errors = self.rule_engine.validate_rules()
        
        if not errors:
            return "All rules are valid."
        
        lines = [f"Found {len(errors)} rule validation errors:"]
        for error in errors:
            lines.append(f"- {error}")
        
        return "\n".join(lines)
    
    @sk_function(
        description="Get applicable rules for current facts",
        name="get_applicable_rules"
    )
    def get_applicable_rules(self, context: "SKContext") -> str:
        """Get rules that can fire given current facts."""
        all_facts = self.fact_store.get_all_facts()
        applicable_rules = self.rule_engine.get_applicable_rules(all_facts)
        
        if not applicable_rules:
            return "No rules are applicable to the current facts."
        
        lines = [f"Found {len(applicable_rules)} applicable rules:"]
        for rule in applicable_rules:
            lines.append(f"- {rule.id} (priority: {rule.priority})")
        
        return "\n".join(lines)


def register_symbolica_plugin(kernel: "Kernel", plugin: SymbolicaPlugin, plugin_name: str = "symbolica") -> None:
    """Register the Symbolica plugin with a Semantic Kernel instance.
    
    Args:
        kernel: The Semantic Kernel instance
        plugin: The Symbolica plugin to register
        plugin_name: Name to register the plugin under
    """
    if not SEMANTIC_KERNEL_AVAILABLE:
        raise ImportError("Semantic Kernel is not available")
    
    kernel.import_plugin(plugin, plugin_name)


# Example usage function
def create_symbolica_kernel(rules: List[Rule], llm_bridge: Optional[LLMBridge] = None) -> "Kernel":
    """Create a Semantic Kernel instance with Symbolica plugin pre-configured.
    
    Args:
        rules: List of rules for the reasoning engine
        llm_bridge: Optional LLM bridge for explanations
        
    Returns:
        Configured Semantic Kernel instance
    """
    if not SEMANTIC_KERNEL_AVAILABLE:
        raise ImportError("Semantic Kernel is not available")
    
    # Create kernel
    kernel = Kernel()
    
    # Create and register Symbolica plugin
    rule_engine = RuleEngine(rules)
    plugin = SymbolicaPlugin(rule_engine, llm_bridge)
    register_symbolica_plugin(kernel, plugin)
    
    return kernel


# Example Semantic Kernel plan templates
EXAMPLE_PLANS = {
    "fact_analysis": """
    {{symbolica.add_facts_json input=$facts}}
    {{symbolica.run_inference}}
    {{symbolica.explain_reasoning}}
    """,
    
    "rule_validation": """
    {{symbolica.validate_rules}}
    {{symbolica.get_statistics}}
    {{symbolica.get_applicable_rules}}
    """,
    
    "fact_exploration": """
    {{symbolica.summarize_facts}}
    {{symbolica.query_facts pattern=$query_pattern}}
    """
} 
"""LangGraph integration hooks for Symbolica."""

from typing import Any, Dict, List, Optional, TypedDict

try:
    from langgraph import Graph
    from langgraph.graph import StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Define minimal types for graceful degradation
    class Graph:
        pass
    class StateGraph:
        def __init__(self, *args, **kwargs):
            pass

from ..core.fact_store import FactStore
from ..core.rule_engine import RuleEngine
from ..core.inference import Inference
from ..core.types import Fact, Rule, Conclusion
from .llm_bridge import LLMBridge


class SymbolicaState(TypedDict):
    """State structure for LangGraph integration."""
    facts: Dict[str, Any]
    conclusions: List[Dict[str, Any]]
    reasoning_trace: Optional[str]
    symbolic_explanation: Optional[str]
    messages: List[Dict[str, str]]


class SymbolicaNode:
    """LangGraph node for symbolic reasoning."""
    
    def __init__(
        self,
        rules: List[Rule],
        llm_bridge: Optional[LLMBridge] = None,
        fact_store: Optional[FactStore] = None,
        node_name: str = "symbolic_reasoning"
    ):
        """Initialize the Symbolica node.
        
        Args:
            rules: List of rules for reasoning
            llm_bridge: Optional LLM bridge for explanations
            fact_store: Optional pre-populated fact store
            node_name: Name of the node in the graph
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph is not available. Install with: pip install langgraph")
        
        self.rules = rules
        self.llm_bridge = llm_bridge
        self.fact_store = fact_store or FactStore()
        self.node_name = node_name
        
        # Initialize reasoning components
        self.rule_engine = RuleEngine(rules)
        self.inference = Inference(self.rule_engine)
    
    def __call__(self, state: SymbolicaState) -> SymbolicaState:
        """Execute symbolic reasoning on the current state.
        
        Args:
            state: Current LangGraph state
            
        Returns:
            Updated state with symbolic reasoning results
        """
        # Clear previous facts and load new ones
        self.fact_store.clear()
        
        # Load facts from state
        for key, value in state.get("facts", {}).items():
            self.fact_store.add(key, value, {"source": "langraph_state"})
        
        # Run inference
        result = self.inference.run(self.fact_store)
        
        # Convert conclusions to serializable format
        conclusions_data = []
        for conclusion in result.conclusions:
            conclusions_data.append({
                "fact_key": conclusion.fact.key,
                "fact_value": conclusion.fact.value,
                "confidence": conclusion.confidence,
                "rule_id": conclusion.rule_id,
                "metadata": conclusion.metadata
            })
        
        # Generate explanations if LLM bridge is available
        reasoning_trace = None
        symbolic_explanation = None
        
        if self.llm_bridge:
            reasoning_trace = self.llm_bridge.explain_trace(result.trace)
            
            if result.conclusions:
                # Explain the first conclusion as an example
                symbolic_explanation = self.llm_bridge.explain_conclusion(
                    result.conclusions[0]
                )
        
        # Update state
        updated_state = state.copy()
        updated_state["conclusions"] = conclusions_data
        updated_state["reasoning_trace"] = reasoning_trace
        updated_state["symbolic_explanation"] = symbolic_explanation
        
        # Add summary message
        if "messages" not in updated_state:
            updated_state["messages"] = []
        
        summary_msg = f"Symbolic reasoning completed: {len(result.conclusions)} conclusions drawn"
        updated_state["messages"].append({
            "role": "system",
            "content": summary_msg
        })
        
        return updated_state
    
    def create_symbolic_workflow(self) -> StateGraph:
        """Create a complete LangGraph workflow with symbolic reasoning.
        
        Returns:
            Configured StateGraph with symbolic reasoning node
        """
        workflow = StateGraph(SymbolicaState)
        
        # Add the symbolic reasoning node
        workflow.add_node(self.node_name, self)
        
        # Set as entry point
        workflow.set_entry_point(self.node_name)
        
        # Set as finish point (can be changed by user)
        workflow.set_finish_point(self.node_name)
        
        return workflow
    
    def add_to_workflow(self, workflow: StateGraph, 
                       upstream_nodes: Optional[List[str]] = None,
                       downstream_nodes: Optional[List[str]] = None) -> None:
        """Add this node to an existing workflow.
        
        Args:
            workflow: Existing StateGraph workflow
            upstream_nodes: Nodes that should connect to this node
            downstream_nodes: Nodes this node should connect to
        """
        # Add the node
        workflow.add_node(self.node_name, self)
        
        # Add upstream connections
        if upstream_nodes:
            for upstream in upstream_nodes:
                workflow.add_edge(upstream, self.node_name)
        
        # Add downstream connections
        if downstream_nodes:
            for downstream in downstream_nodes:
                workflow.add_edge(self.node_name, downstream)
    
    def update_rules(self, new_rules: List[Rule]) -> None:
        """Update the rules used by this node.
        
        Args:
            new_rules: New list of rules
        """
        self.rules = new_rules
        self.rule_engine = RuleEngine(new_rules)
        self.inference = Inference(self.rule_engine)


def create_fact_extraction_node(
    extraction_prompt: str,
    llm_client: Any,
    node_name: str = "fact_extraction"
) -> callable:
    """Create a node that extracts facts from messages using an LLM.
    
    Args:
        extraction_prompt: Prompt template for fact extraction
        llm_client: LLM client for extraction
        node_name: Name of the node
        
    Returns:
        Callable node function
    """
    def extract_facts(state: SymbolicaState) -> SymbolicaState:
        """Extract facts from the last message."""
        messages = state.get("messages", [])
        if not messages:
            return state
        
        last_message = messages[-1]
        if last_message.get("role") != "user":
            return state
        
        # Build extraction prompt
        prompt = extraction_prompt.format(message=last_message["content"])
        
        try:
            # Call LLM for fact extraction
            if hasattr(llm_client, 'chat'):
                response = llm_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500
                )
                extracted_text = response.choices[0].message.content
            else:
                extracted_text = llm_client.generate(prompt)
            
            # Parse extracted facts (simple key=value format)
            facts = {}
            for line in extracted_text.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    facts[key.strip()] = value.strip()
            
            # Update state
            updated_state = state.copy()
            updated_state["facts"] = {**state.get("facts", {}), **facts}
            
            return updated_state
            
        except Exception as e:
            # Return original state if extraction fails
            return state
    
    extract_facts.__name__ = node_name
    return extract_facts


def create_explanation_node(
    llm_bridge: LLMBridge,
    node_name: str = "symbolic_explanation"
) -> callable:
    """Create a node that generates natural language explanations.
    
    Args:
        llm_bridge: LLM bridge for generating explanations
        node_name: Name of the node
        
    Returns:
        Callable node function
    """
    def generate_explanation(state: SymbolicaState) -> SymbolicaState:
        """Generate explanation from reasoning trace."""
        reasoning_trace = state.get("reasoning_trace")
        conclusions = state.get("conclusions", [])
        
        if not reasoning_trace and not conclusions:
            return state
        
        explanation_parts = []
        
        if reasoning_trace:
            explanation_parts.append("Here's how I reasoned through this:")
            explanation_parts.append(reasoning_trace)
        
        if conclusions:
            explanation_parts.append("\nKey conclusions:")
            for conclusion in conclusions[:3]:  # Limit to first 3
                explanation_parts.append(
                    f"- {conclusion['fact_key']}: {conclusion['fact_value']} "
                    f"(confidence: {conclusion['confidence']:.0%})"
                )
        
        explanation = "\n".join(explanation_parts)
        
        # Update state
        updated_state = state.copy()
        if "messages" not in updated_state:
            updated_state["messages"] = []
        
        updated_state["messages"].append({
            "role": "assistant",
            "content": explanation
        })
        
        return updated_state
    
    generate_explanation.__name__ = node_name
    return generate_explanation


# Example usage patterns
EXAMPLE_EXTRACTION_PROMPT = """
Extract factual information from the following message in key=value format:

Message: {message}

Extract facts like:
- entity_type=value
- status=value  
- metric=value
- condition=value

Only extract clear, objective facts. One fact per line.
"""

EXAMPLE_RULES = [
    # This would be populated with actual Rule objects
    # Rule(
    #     id="server_down_rule",
    #     conditions=[
    #         Condition(field="status", operator=OperatorType.EQ, value="down"),
    #         Condition(field="entity_type", operator=OperatorType.EQ, value="server")
    #     ],
    #     conclusions=[
    #         Conclusion(
    #             fact=Fact(key="alert_severity", value="high"),
    #             confidence=0.9,
    #             rule_id="server_down_rule"
    #         )
    #     ]
    # )
] 
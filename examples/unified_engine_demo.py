#!/usr/bin/env python3
"""
Demonstration of Unified RuleEngine Architecture.

Shows three approaches to unify the standard and optimized engines:
1. Auto-selecting engine based on rule count
2. Unified engine with optimization flags
3. Adaptive engine that switches strategies dynamically
"""

from symbolica import FactStore, RuleEngine
from symbolica.core.optimized_rule_engine import OptimizedRuleEngine
from symbolica.parsers.yaml_parser import YAMLRuleParser
from pathlib import Path
from typing import List, Optional
import time


class UnifiedRuleEngine:
    """
    Approach 1: Auto-selecting engine based on workload characteristics.
    
    Automatically chooses between standard and optimized engines based on:
    - Number of rules
    - Number of facts
    - Previous performance metrics
    """
    
    def __init__(self, rules: List, auto_optimize: bool = True, optimization_threshold: int = 50):
        """Initialize with automatic optimization selection."""
        self.rules = rules
        self.auto_optimize = auto_optimize
        self.optimization_threshold = optimization_threshold
        
        # Choose engine based on rule count
        if auto_optimize and len(rules) >= optimization_threshold:
            print(f"🚀 Auto-selected OptimizedRuleEngine ({len(rules)} rules >= {optimization_threshold})")
            self.engine = OptimizedRuleEngine(rules)
            self.engine_type = "optimized"
        else:
            print(f"⚡ Auto-selected StandardRuleEngine ({len(rules)} rules < {optimization_threshold})")
            self.engine = RuleEngine(rules)
            self.engine_type = "standard"
    
    def evaluate(self, facts: FactStore, max_iterations: int = 100):
        """Evaluate using the selected engine."""
        if self.engine_type == "optimized":
            return self.engine.evaluate_optimized(facts, max_iterations)
        else:
            return self.engine.evaluate(facts, max_iterations)
    
    def get_engine_info(self):
        """Get information about the selected engine."""
        return {
            "engine_type": self.engine_type,
            "rule_count": len(self.rules),
            "optimization_threshold": self.optimization_threshold,
            "auto_optimize": self.auto_optimize
        }


class ConfigurableRuleEngine:
    """
    Approach 2: Single engine with configurable optimization levels.
    
    One engine with different optimization strategies:
    - BASIC: Standard evaluation
    - INDEXED: Fact-to-rule indexing only
    - CACHED: Indexing + condition caching
    - FULL: All optimizations enabled
    """
    
    def __init__(self, rules: List, optimization_level: str = "AUTO"):
        """Initialize with configurable optimization level."""
        self.rules = rules
        self.optimization_level = optimization_level
        
        # Auto-select optimization level based on rule count
        if optimization_level == "AUTO":
            if len(rules) < 25:
                self.optimization_level = "BASIC"
            elif len(rules) < 100:
                self.optimization_level = "INDEXED"
            elif len(rules) < 500:
                self.optimization_level = "CACHED"
            else:
                self.optimization_level = "FULL"
        
        print(f"🎛️  ConfigurableRuleEngine: {self.optimization_level} optimization ({len(rules)} rules)")
        
        # Initialize based on optimization level
        if self.optimization_level == "BASIC":
            self.engine = RuleEngine(rules)
        else:
            self.engine = OptimizedRuleEngine(rules)
    
    def evaluate(self, facts: FactStore, max_iterations: int = 100):
        """Evaluate with the configured optimization level."""
        if self.optimization_level == "BASIC":
            return self.engine.evaluate(facts, max_iterations)
        else:
            # Could implement different optimization levels here
            return self.engine.evaluate_optimized(facts, max_iterations)
    
    def get_optimization_info(self):
        """Get optimization configuration info."""
        return {
            "optimization_level": self.optimization_level,
            "rule_count": len(self.rules),
            "available_levels": ["BASIC", "INDEXED", "CACHED", "FULL", "AUTO"]
        }


class AdaptiveRuleEngine:
    """
    Approach 3: Adaptive engine that learns and switches strategies.
    
    Monitors performance and adapts optimization strategy:
    - Starts with one approach
    - Measures performance over time
    - Switches to better strategy if detected
    """
    
    def __init__(self, rules: List):
        """Initialize adaptive engine."""
        self.rules = rules
        self.performance_history = []
        self.current_strategy = "standard"
        self.switch_threshold_ms = 5.0  # Switch if >5ms inference time
        
        # Start with standard engine
        self.standard_engine = RuleEngine(rules)
        self.optimized_engine = None  # Lazy initialization
        
        print(f"🧠 AdaptiveRuleEngine: Starting with standard strategy ({len(rules)} rules)")
    
    def evaluate(self, facts: FactStore, max_iterations: int = 100):
        """Evaluate with adaptive strategy selection."""
        start_time = time.time()
        
        if self.current_strategy == "standard":
            conclusions = self.standard_engine.evaluate(facts, max_iterations)
        else:  # optimized
            if self.optimized_engine is None:
                print("   🚀 Initializing optimized engine...")
                self.optimized_engine = OptimizedRuleEngine(self.rules)
            conclusions = self.optimized_engine.evaluate_optimized(facts, max_iterations)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Record performance
        self.performance_history.append({
            "strategy": self.current_strategy,
            "execution_time_ms": execution_time_ms,
            "fact_count": len(facts.get_all_facts()),
            "conclusion_count": len(conclusions)
        })
        
        # Adaptive strategy switching
        self._adapt_strategy(execution_time_ms)
        
        return conclusions
    
    def _adapt_strategy(self, execution_time_ms: float):
        """Adapt strategy based on performance."""
        if (self.current_strategy == "standard" and 
            execution_time_ms > self.switch_threshold_ms and 
            len(self.rules) > 20):
            
            print(f"   📈 Switching to optimized strategy (inference took {execution_time_ms:.2f}ms)")
            self.current_strategy = "optimized"
        
        elif (self.current_strategy == "optimized" and 
              len(self.performance_history) > 5):
            
            # Check if standard might be better for small workloads
            recent_times = [h["execution_time_ms"] for h in self.performance_history[-5:]]
            avg_time = sum(recent_times) / len(recent_times)
            
            if avg_time < 1.0 and len(self.rules) < 50:
                print(f"   📉 Switching back to standard strategy (avg time: {avg_time:.2f}ms)")
                self.current_strategy = "standard"
    
    def get_adaptation_info(self):
        """Get information about adaptive behavior."""
        if not self.performance_history:
            return {"current_strategy": self.current_strategy, "history_count": 0}
        
        recent_performance = self.performance_history[-5:] if len(self.performance_history) >= 5 else self.performance_history
        avg_time = sum(h["execution_time_ms"] for h in recent_performance) / len(recent_performance)
        
        return {
            "current_strategy": self.current_strategy,
            "history_count": len(self.performance_history),
            "recent_avg_time_ms": avg_time,
            "switch_threshold_ms": self.switch_threshold_ms
        }


def demonstrate_unified_approaches():
    """Demonstrate the three unified engine approaches."""
    print("🔧 Unified RuleEngine Architecture Demonstration")
    print("=" * 60)
    
    # Load rules from multiple domains
    all_rules = []
    parser = YAMLRuleParser()
    
    domains = ["database-troubleshooting", "income-tax", "insurance-claims"]
    for domain in domains:
        rules_folder = Path(__file__).parent / domain
        if rules_folder.exists():
            domain_rules = parser.parse_rules_from_folder(str(rules_folder))
            all_rules.extend(domain_rules)
    
    print(f"📊 Loaded {len(all_rules)} rules from {len(domains)} domains\n")
    
    # Create test facts
    facts = FactStore()
    facts.add("cpu_utilization", 95.0, {"source": "monitoring"})
    facts.add("claim_amount", 75000, {"source": "claim_form"})
    facts.add("adjusted_gross_income", 85000, {"source": "tax_return"})
    
    # Approach 1: Auto-selecting Engine
    print("1️⃣  Auto-Selecting Engine Approach")
    print("-" * 40)
    
    unified_engine = UnifiedRuleEngine(all_rules, auto_optimize=True, optimization_threshold=25)
    start_time = time.time()
    conclusions1 = unified_engine.evaluate(facts)
    time1 = (time.time() - start_time) * 1000
    
    info1 = unified_engine.get_engine_info()
    print(f"   Selected: {info1['engine_type']} engine")
    print(f"   Inference time: {time1:.2f}ms")
    print(f"   Conclusions: {len(conclusions1)}")
    
    # Approach 2: Configurable Engine
    print(f"\n2️⃣  Configurable Engine Approach")
    print("-" * 40)
    
    configurable_engine = ConfigurableRuleEngine(all_rules, optimization_level="AUTO")
    start_time = time.time()
    conclusions2 = configurable_engine.evaluate(facts)
    time2 = (time.time() - start_time) * 1000
    
    info2 = configurable_engine.get_optimization_info()
    print(f"   Optimization level: {info2['optimization_level']}")
    print(f"   Inference time: {time2:.2f}ms")
    print(f"   Conclusions: {len(conclusions2)}")
    
    # Approach 3: Adaptive Engine
    print(f"\n3️⃣  Adaptive Engine Approach")
    print("-" * 40)
    
    adaptive_engine = AdaptiveRuleEngine(all_rules)
    
    # Run multiple times to show adaptation
    for i in range(3):
        start_time = time.time()
        conclusions3 = adaptive_engine.evaluate(facts)
        time3 = (time.time() - start_time) * 1000
        
        info3 = adaptive_engine.get_adaptation_info()
        print(f"   Run {i+1}: {info3['current_strategy']} strategy, {time3:.2f}ms, {len(conclusions3)} conclusions")
    
    # Final adaptation info
    final_info = adaptive_engine.get_adaptation_info()
    print(f"   Final strategy: {final_info['current_strategy']}")
    print(f"   Performance history: {final_info['history_count']} runs")
    
    # Summary
    print(f"\n📋 Architecture Comparison Summary")
    print("=" * 60)
    print(f"Approach 1 (Auto-Select): {info1['engine_type']} engine, {time1:.2f}ms")
    print(f"Approach 2 (Configurable): {info2['optimization_level']} level, {time2:.2f}ms") 
    print(f"Approach 3 (Adaptive): {final_info['current_strategy']} strategy, {final_info['recent_avg_time_ms']:.2f}ms avg")
    
    print(f"\n💡 Recommendations:")
    print(f"• Auto-Select: Best for simple deployment (set threshold once)")
    print(f"• Configurable: Best for fine-tuned control (different workloads)")
    print(f"• Adaptive: Best for dynamic environments (learns over time)")


if __name__ == "__main__":
    demonstrate_unified_approaches() 
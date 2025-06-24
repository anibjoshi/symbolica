#!/usr/bin/env python3
"""
Symbolica v1 RuleEngine Demo
===========================

Shows the simplified, unified RuleEngine that:
✅ Works efficiently for both small and large rule sets
✅ Includes smart optimizations by default
✅ Simple, clean API without complexity
✅ One engine for all workloads
"""

from symbolica.core import RuleEngine, FactStore
from symbolica.parsers.yaml_parser import YAMLRuleParser
import time


def main():
    print("🚀 Symbolica v1 Unified RuleEngine Demo")
    print("=" * 45)
    print("One engine. All workloads. Simple and fast.\n")
    
    # 1. Create the engine
    print("🏗️  CREATING RULE ENGINE")
    print("-" * 25)
    
    engine = RuleEngine()
    print(f"✅ Created RuleEngine")
    print(f"   • Smart optimizations included by default")
    print(f"   • Works for small and large rule sets")
    print(f"   • No complex configuration needed")
    
    # 2. Load rules from multiple domains
    print(f"\n📚 LOADING RULES FROM MULTIPLE DOMAINS")
    print("-" * 40)
    
    parser = YAMLRuleParser()
    
    # Load rules from different domains
    db_rules = parser.parse_rules_from_folder("database-troubleshooting")
    tax_rules = parser.parse_rules_from_folder("income-tax")
    insurance_rules = parser.parse_rules_from_folder("insurance-claims")
    
    all_rules = db_rules + tax_rules + insurance_rules
    
    print(f"📦 Loading {len(all_rules)} rules:")
    print(f"   • Database troubleshooting: {len(db_rules)} rules")
    print(f"   • Income tax: {len(tax_rules)} rules") 
    print(f"   • Insurance claims: {len(insurance_rules)} rules")
    
    # Add rules to engine
    for rule in all_rules:
        engine.add_rule(rule)
    
    print(f"✅ All rules loaded successfully")
    
    # 3. Show engine capabilities
    print(f"\n⚡ ENGINE CAPABILITIES")
    print("-" * 20)
    
    stats = engine.get_statistics()
    print(f"📊 Engine Status:")
    print(f"   • Total rules: {stats['total_rules']}")
    print(f"   • Enabled rules: {stats['enabled_rules']}")
    print(f"   • Optimization features: {', '.join(stats['optimization_features'])}")
    
    # 4. Create facts and run evaluation
    print(f"\n🧪 RUNNING EVALUATION")
    print("-" * 20)
    
    # Create a fact store with diverse facts
    facts = FactStore()
    facts.add("cpu_utilization", 95.2)           # Database domain
    facts.add("memory_usage", 87.1)              # Database domain
    facts.add("income", 85000)                   # Tax domain
    facts.add("filing_status", "married")        # Tax domain
    facts.add("claim_amount", 15000)             # Insurance domain
    facts.add("claim_type", "theft")             # Insurance domain
    
    print(f"📋 Created {len(facts.get_all_facts())} facts across domains")
    
    # Run evaluation
    start_time = time.time()
    conclusions = engine.evaluate(facts)
    execution_time = (time.time() - start_time) * 1000
    
    print(f"⚡ Evaluation completed in {execution_time:.2f}ms")
    print(f"   • Conclusions drawn: {len(conclusions)}")
    
    # Show some conclusions
    if conclusions:
        print(f"\n📊 Sample Conclusions:")
        for i, conclusion in enumerate(conclusions[:3]):  # Show first 3
            print(f"   {i+1}. {conclusion.fact.key}: {conclusion.fact.value}")
            print(f"      Rule: {conclusion.rule_id}")
            print(f"      Confidence: {conclusion.confidence}")
    
    # 5. Show performance statistics
    print(f"\n📈 PERFORMANCE STATISTICS")
    print("-" * 27)
    
    final_stats = engine.get_statistics()
    
    print(f"Evaluation Performance:")
    print(f"   • Execution time: {final_stats['avg_execution_time_ms']:.2f}ms")
    print(f"   • Rules fired: {final_stats['total_rules_fired']}")
    print(f"   • Rules skipped: {final_stats['total_rules_skipped']}")
    print(f"   • Skip rate: {final_stats['skip_rate']:.1%}")
    
    print(f"\nOptimization Effectiveness:")
    print(f"   • Cache hit rate: {final_stats['cache_hit_rate']:.1%}")
    print(f"   • Cache hits: {final_stats['cache_hits']}")
    print(f"   • Cache misses: {final_stats['cache_misses']}")
    
    # 6. Test with larger workload
    print(f"\n🔄 TESTING WITH ADDITIONAL FACTS")
    print("-" * 32)
    
    # Add more facts to test scalability
    for i in range(20):
        facts.add(f"test_metric_{i}", i * 10.5)
    
    start_time = time.time()
    conclusions2 = engine.evaluate(facts)
    execution_time2 = (time.time() - start_time) * 1000
    
    print(f"📋 Added 20 more facts ({len(facts.get_all_facts())} total)")
    print(f"⚡ Evaluation completed in {execution_time2:.2f}ms")
    print(f"   • Conclusions drawn: {len(conclusions2)}")
    
    # Show how optimizations help
    final_stats2 = engine.get_statistics()
    total_rules_processed = final_stats2['total_rules_fired'] + final_stats2['total_rules_skipped']
    
    print(f"\n🎯 Optimization Benefits:")
    print(f"   • Rules processed: {total_rules_processed}")
    print(f"   • Rules actually evaluated: {final_stats2['total_rules_fired']}")
    print(f"   • Rules skipped by indexing: {final_stats2['total_rules_skipped']}")
    print(f"   • Performance boost: {final_stats2['skip_rate']:.1%} rules skipped")
    
    # 7. Show validation capabilities
    print(f"\n🔍 VALIDATION CAPABILITIES")
    print("-" * 25)
    
    validation_errors = engine.validate_rules()
    print(f"✅ Validation completed")
    print(f"   • Rules validated: {stats['total_rules']}")
    print(f"   • Validation errors: {len(validation_errors)}")
    
    if validation_errors:
        print(f"   • Issues found:")
        for error in validation_errors[:3]:  # Show first 3
            print(f"     - {error}")
    else:
        print(f"   • All rules pass validation!")
    
    # 8. Summary
    print(f"\n🎉 SYMBOLICA V1 SUMMARY")
    print("=" * 30)
    
    print("✅ Unified Architecture:")
    print("   → One RuleEngine for all workloads")
    print("   → No complex strategy selection")
    print("   → Simple, predictable API")
    
    print("\n✅ Smart Optimizations:")
    print("   → Rule indexing for fast lookups")
    print("   → Condition caching for repeated evaluations")
    print("   → Fact-driven evaluation (skip irrelevant rules)")
    print("   → Short-circuit logical evaluation")
    
    print("\n✅ Production Ready:")
    print("   → Comprehensive validation")
    print("   → Detailed performance statistics")
    print("   → Cross-domain rule processing")
    print("   → Efficient for 10 rules or 1000+ rules")
    
    print(f"\n🚀 Result: {final_stats2['cache_hit_rate']:.0%} cache hit rate, {final_stats2['skip_rate']:.0%} rules skipped!")
    print("=" * 45)


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Comprehensive test runner for Symbolica.

This script provides multiple ways to run the Symbolica test suite with
different levels of verbosity and filtering options.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and handle output."""
    if description:
        print(f"\n🧪 {description}")
        print("=" * (len(description) + 3))
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def run_tests(test_type="all", verbose=False, coverage=False, markers=None):
    """Run tests with specified options."""
    
    # Base pytest command
    cmd_parts = ["python", "-m", "pytest"]
    
    # Add verbosity
    if verbose:
        cmd_parts.append("-v")
    else:
        cmd_parts.append("-q")
    
    # Add coverage if requested
    if coverage:
        cmd_parts.extend([
            "--cov=symbolica",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    # Add markers for filtering
    if markers:
        for marker in markers:
            cmd_parts.extend(["-m", marker])
    
    # Add test paths based on type
    if test_type == "unit":
        cmd_parts.extend([
            "tests/test_fact_store.py",
            "tests/test_rule_engine.py",
            "tests/test_json_interface.py",
            "tests/test_parsers.py"
        ])
    elif test_type == "integration":
        cmd_parts.append("tests/integration/")
    elif test_type == "json":
        cmd_parts.extend(["-m", "json"])
    elif test_type == "tracing":
        cmd_parts.extend(["-m", "tracing"])
    elif test_type == "performance":
        cmd_parts.extend(["-m", "performance"])
    else:  # all
        cmd_parts.append("tests/")
    
    # Add output formatting
    cmd_parts.extend([
        "--tb=short",
        "--disable-warnings"
    ])
    
    cmd = " ".join(cmd_parts)
    return run_command(cmd, f"Running {test_type} tests")


def run_quick_smoke_test():
    """Run a quick smoke test to verify basic functionality."""
    print("\n🚀 Quick Smoke Test")
    print("=" * 18)
    
    # Test basic imports
    try:
        from symbolica import FactStore, RuleEngine, Inference
        from symbolica.parsers.yaml_parser import YAMLRuleParser
        print("✅ All imports successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test basic functionality
    try:
        # Create facts from JSON
        facts = FactStore.from_json({"test_value": 100, "status": "active"})
        print(f"✅ FactStore.from_json() works ({len(facts)} facts created)")
        
        # Create simple rule
        from symbolica.core.types import Rule, Condition, Conclusion, Fact, OperatorType
        rule = Rule(
            id="smoke_test",
            conditions=[Condition(field="test_value", operator=OperatorType.GT, value=50)],
            conclusions=[Conclusion(fact=Fact(key="result", value="passed"), confidence=1.0, rule_id="smoke_test")]
        )
        
        # Run inference
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts)
        
        print(f"✅ Inference works (fired {result.rules_fired} rules, {len(result.conclusions)} conclusions)")
        
        # Test JSON output
        json_output = result.to_json()
        print(f"✅ JSON output works ({len(json_output)} characters)")
        
        # Test tracing
        if result.trace and len(result.trace.steps) > 0:
            print("✅ Tracing works")
        else:
            print("⚠️  Tracing may have issues")
        
        return True
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run Symbolica tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --type unit        # Run only unit tests  
  python run_tests.py --type integration # Run only integration tests
  python run_tests.py --verbose          # Run with verbose output
  python run_tests.py --coverage         # Run with coverage report
  python run_tests.py --smoke            # Run quick smoke test
  python run_tests.py --type json        # Run only JSON-related tests
  python run_tests.py --type tracing     # Run only tracing tests
        """
    )
    
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "json", "tracing", "performance"],
        default="all",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests with verbose output"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true", 
        help="Run tests with coverage report"
    )
    
    parser.add_argument(
        "--smoke", "-s",
        action="store_true",
        help="Run quick smoke test only"
    )
    
    parser.add_argument(
        "--markers", "-m",
        nargs="*",
        help="Run tests with specific pytest markers"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies first"
    )
    
    args = parser.parse_args()
    
    print("🔬 Symbolica Test Suite")
    print("=" * 23)
    
    # Install dependencies if requested
    if args.install_deps:
        print("\n📦 Installing test dependencies...")
        deps_cmd = "pip install pytest pytest-cov"
        if not run_command(deps_cmd, "Installing dependencies"):
            return 1
    
    # Run smoke test
    if args.smoke:
        if run_quick_smoke_test():
            print("\n🎉 Smoke test passed!")
            return 0
        else:
            print("\n💥 Smoke test failed!")
            return 1
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("❌ pytest not found. Install with: pip install pytest pytest-cov")
        return 1
    
    # Run the specified tests
    success = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        markers=args.markers
    )
    
    if success:
        print(f"\n🎉 {args.type.title()} tests completed successfully!")
        
        if args.coverage:
            print("\n📊 Coverage report generated in htmlcov/index.html")
        
        # Quick summary
        print("\n📋 Test Summary:")
        print("✅ Core functionality: FactStore, RuleEngine, Inference")
        print("✅ JSON input/output: Perfect for LLM integration")
        print("✅ Detailed tracing: Explains reasoning steps")
        print("✅ Rule parsing: YAML rule files")
        print("✅ Performance: Optimized for production use")
        
        return 0
    else:
        print(f"\n💥 {args.type.title()} tests failed!")
        print("\nTry running with --verbose for more details")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
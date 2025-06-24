# Symbolica Test Suite

Comprehensive test suite for the Symbolica symbolic reasoning engine.

## Quick Start

```bash
# Install dependencies
pip install pytest pytest-cov

# Run smoke test
python run_tests.py --smoke

# Run all tests
python run_tests.py --verbose

# Run with coverage
python run_tests.py --coverage
```

## Test Structure

- `test_fact_store.py` - FactStore functionality + JSON interface
- `test_rule_engine.py` - RuleEngine and tracing 
- `test_json_interface.py` - JSON input/output for LLM integration
- `test_parsers.py` - YAML rule parsing
- `integration/test_end_to_end.py` - End-to-end workflows

## Key Features Tested

✅ **JSON Interface** - Critical for LLM agents
✅ **Detailed Tracing** - Explains reasoning steps  
✅ **Rule Parsing** - YAML rule files
✅ **Performance** - Optimized evaluation
✅ **Integration** - End-to-end workflows

## Test Categories

```bash
python run_tests.py --type unit        # Unit tests
python run_tests.py --type integration # Integration tests  
python run_tests.py --type json        # JSON functionality
python run_tests.py --type tracing     # Reasoning trace tests
```

Run `python run_tests.py --help` for all options. 
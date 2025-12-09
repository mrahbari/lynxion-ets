#!/usr/bin/env python3
"""Test runner for all WFO-related tests in the lynxion-ets system."""

import unittest
import sys
import os
from pathlib import Path

# Add the project root to sys.path to ensure imports work
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_all_wfo_tests():
    """Run all WFO-related tests in the system."""
    print("=" * 90)
    print(" lynxion-ets: COMPREHENSIVE WFO TEST SUITE RUNNER")
    print("=" * 90)
    print(f"Project Root: {project_root}")
    print(f"Python Path: {sys.path[0]}")
    print()
    
    # Import and run each test module separately to ensure comprehensive coverage
    test_results = {}
    
    # 1. Run the initial comprehensive tests
    print("🧪 Running initial comprehensive WFO tests...")
    try:
        from tests.wfo_comprehensive_tests import run_wfo_tests
        initial_success = run_wfo_tests()
        test_results['initial_comprehensive'] = initial_success
        print("✅ Initial comprehensive tests completed\n")
    except ImportError as e:
        print(f"❌ Failed to import initial comprehensive tests: {e}")
        test_results['initial_comprehensive'] = False
    except Exception as e:
        print(f"❌ Error running initial comprehensive tests: {e}")
        test_results['initial_comprehensive'] = False
    
    # 2. Run the advanced tests
    print("🔬 Running advanced WFO tests with realistic data...")
    try:
        from tests.wfo_advanced_tests import run_advanced_wfo_tests
        advanced_success = run_advanced_wfo_tests()
        test_results['advanced_realistic'] = advanced_success
        print("✅ Advanced tests completed\n")
    except ImportError as e:
        print(f"❌ Failed to import advanced tests: {e}")
        test_results['advanced_realistic'] = False
    except Exception as e:
        print(f"❌ Error running advanced tests: {e}")
        test_results['advanced_realistic'] = False
    
    # 3. Run the complete pipeline integration tests
    print("🔄 Running complete WFO pipeline integration tests...")
    try:
        from tests.wfo_complete_pipeline_tests import run_complete_pipeline_tests
        pipeline_success = run_complete_pipeline_tests()
        test_results['complete_pipeline'] = pipeline_success
        print("✅ Complete pipeline tests completed\n")
    except ImportError as e:
        print(f"❌ Failed to import complete pipeline tests: {e}")
        test_results['complete_pipeline'] = False
    except Exception as e:
        print(f"❌ Error running complete pipeline tests: {e}")
        test_results['complete_pipeline'] = False
    
    # 4. Run unittest-based tests for any remaining WFO-related test files
    print("🔍 Running additional WFO unittest-based tests...")
    
    # Discover and run any other WFO-related test files in the tests directory
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Look for all test files that might contain WFO tests
    test_dir = project_root / "tests"
    if test_dir.exists():
        for test_file in test_dir.glob("test_*wfo*.py"):
            try:
                # Import the module dynamically
                import importlib.util
                spec = importlib.util.spec_from_file_location(test_file.stem, test_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Load all test cases from the module
                for name in dir(module):
                    obj = getattr(module, name)
                    if (isinstance(obj, type) and 
                        issubclass(obj, unittest.TestCase) and 
                        obj != unittest.TestCase):
                        suite.addTests(loader.loadTestsFromTestCase(obj))
                        
            except Exception as e:
                print(f"⚠️  Could not load tests from {test_file.name}: {e}")
    
    # Also look for any test classes in the main WFO modules
    wfo_modules = [
        "application.walk_forward.wfo_orchestrator",
        "application.walk_forward.sliding_window_splitter", 
        "application.walk_forward.hyperopt_adapter",
        "application.walk_forward.cross_validation_engine"
    ]
    
    for module_name in wfo_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            # Look for test classes in the module
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and 
                    issubclass(obj, unittest.TestCase) and 
                    obj != unittest.TestCase):
                    suite.addTests(loader.loadTestsFromTestCase(obj))
        except ImportError:
            print(f"⚠️  Could not import {module_name} for test discovery")
        except Exception as e:
            print(f"⚠️  Error discovering tests in {module_name}: {e}")
    
    if suite.countTestCases() > 0:
        print(f"Found {suite.countTestCases()} additional test cases via discovery")
        runner = unittest.TextTestRunner(verbosity=1)
        discovery_result = runner.run(suite)
        discovery_success = discovery_result.wasSuccessful()
        test_results['discovery_based'] = discovery_success
    else:
        print("No additional test cases found via discovery")
        test_results['discovery_based'] = True  # Nothing to test, so nothing failed
    
    print("\n" + "=" * 90)
    print(" lynxion-ets: WFO TEST SUITE SUMMARY")
    print("=" * 90)
    
    # Calculate overall success
    all_passed = all(test_results.values())
    
    for test_suite, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_suite:<25} : {status}")
    
    print()
    if all_passed:
        print("🎉 ALL WFO TEST SUITES PASSED!")
        print("The Walk-Forward Optimization system is comprehensively tested and validated.")
    else:
        print("❌ SOME WFO TEST SUITES FAILED!")
        failed_suites = [name for name, passed in test_results.items() if not passed]
        print(f"Failed suites: {', '.join(failed_suites)}")
        print("Please review the specific test failures above.")
    
    print(f"\nTotal Suites: {len(test_results)}")
    print(f"Passed: {sum(test_results.values())}")
    print(f"Failed: {len(test_results) - sum(test_results.values())}")
    print("=" * 90)
    
    return all_passed


def run_specific_wfo_module_tests():
    """Run tests for specific WFO modules directly using unittest."""
    print("\n🔍 Running direct unittest discovery for WFO modules...")
    
    # Create a test suite that discovers WFO-related tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Discover tests in the WFO directory
    wfo_test_path = project_root / "application" / "walk_forward"
    
    if wfo_test_path.exists():
        print(f"Looking for tests in: {wfo_test_path}")
        try:
            # Load tests from the walk_forward package
            wfo_suite = loader.discover(
                start_dir=str(wfo_test_path),
                pattern="test*.py",
                top_level_dir=str(project_root)
            )
            suite.addTest(wfo_suite)
        except Exception as e:
            print(f"⚠️  Could not discover tests in WFO directory: {e}")
    else:
        print(f"⚠️  WFO directory not found: {wfo_test_path}")
    
    # Also check for any tests that might be in main WFO files (if they have test classes)
    try:
        from application.walk_forward.wfo_orchestrator import WFOOrchestrator
        # Add any tests that might be defined in the orchestrator module
    except ImportError:
        pass
    
    if suite.countTestCases() > 0:
        print(f"Running {suite.countTestCases()} discovered WFO tests...")
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()
    else:
        print("No additional WFO tests discovered via direct module testing")
        return True


if __name__ == "__main__":
    # Run the comprehensive test suite
    overall_success = run_all_wfo_tests()
    
    # Also run specific module tests
    module_success = run_specific_wfo_module_tests()
    
    # Final overall result
    final_success = overall_success and module_success
    
    print(f"\n🏁 FINAL RESULT: {'SUCCESS' if final_success else 'FAILURE'}")
    
    if not final_success:
        print("\nSome tests failed. Check the detailed output above for specific failures.")
        sys.exit(1)
    else:
        print("\nAll tests completed successfully!")
        sys.exit(0)
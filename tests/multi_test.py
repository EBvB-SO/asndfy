# multi_test.py
"""
Test script for the refactored phase-based plan generator.
Tests PhaseStructureService, exercise filtering, and full plan generation.
"""
import os
import sys
import json
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.training_plan import PhasePlanRequest, FullPlanRequest
from app.services.plan_generator import PlanGeneratorService
from app.services.phase_structure import PhaseStructureService
from app.services.exercise_filter import ExerciseFilterService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PlanGeneratorTester:
    def __init__(self):
        self.results = {
            "phase_structure": [],
            "exercise_filtering": [],
            "plan_generation": [],
            "errors": []
        }
        
    def log_result(self, category, test_name, success, details=""):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results[category].append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"  Details: {details}")
    
    def test_phase_structure_service(self):
        """Test PhaseStructureService independently"""
        print("\n=== Testing PhaseStructureService ===")
        
        try:
            service = PhaseStructureService()
            self.log_result("phase_structure", "Service initialization", True)
        except Exception as e:
            self.log_result("phase_structure", "Service initialization", False, str(e))
            return
        
        # Test data
        test_data = PhasePlanRequest(
            route="Test Route",
            grade="7b",
            crag="Test Crag",
            route_angles="Overhanging",
            route_lengths="Long",
            hold_types="Crimpy",
            route_description="Sustained crimpy climbing",
            weeks_to_train="8",
            sessions_per_week="4",
            time_per_session="2 hours",
            current_climbing_grade="7a",
            max_boulder_grade="V5",
            training_experience="3 years",
            perceived_strengths="Power",
            perceived_weaknesses="Endurance",
            attribute_ratings="finger_strength:3, endurance:2, power:4",
            training_facilities="Bouldering wall, Fingerboard, Campus board",
            injury_history="None",
            general_fitness="Good",
            height="175cm",
            weight="70kg",
            preferred_climbing_style="Sport",
            indoor_vs_outdoor="Both",
            onsight_flash_level="6c+",
            redpointing_experience="Yes",
            sleep_recovery="Good",
            work_life_balance="Balanced",
            fear_factors="None",
            mindfulness_practices="Sometimes",
            motivation_level="High",
            access_to_coaches="No",
            time_for_cross_training="Yes",
            additional_notes=""
        )
        
        # Test different week configurations
        test_configs = [
            (4, "Short plan (4 weeks)"),
            (8, "Medium plan (8 weeks)"),
            (12, "Long plan (12 weeks)"),
            (16, "Very long plan (16 weeks)")
        ]
        
        for weeks, desc in test_configs:
            try:
                phases = service.determine_phase_structure(
                    test_data,
                    weeks,
                    4,  # sessions per week
                    {"is_endurance": True, "is_crimpy": True},
                    {"finger_strength": 3, "endurance": 2, "power": 4}
                )
                
                # Verify phases
                phase_names = [p['name'] for p in phases]
                total_weeks = sum(p['weeks'] for p in phases)
                
                success = total_weeks == weeks
                details = f"{desc}: {len(phases)} phases = {phase_names}, Total: {total_weeks} weeks"
                
                self.log_result("phase_structure", desc, success, details)
                
                # Check phase types
                phase_types = [p['type'] for p in phases]
                valid_types = all(t in ['base', 'peak', 'taper'] for t in phase_types)
                self.log_result("phase_structure", f"{desc} - Valid phase types", valid_types, f"Types: {phase_types}")
                
            except Exception as e:
                self.log_result("phase_structure", desc, False, str(e))
    
    def test_exercise_filtering(self):
        """Test exercise filtering with phase types"""
        print("\n=== Testing Exercise Filtering ===")
        
        try:
            service = ExerciseFilterService()
            self.log_result("exercise_filtering", "Service initialization", True)
        except Exception as e:
            self.log_result("exercise_filtering", "Service initialization", False, str(e))
            return
        
        # Mock exercises for testing
        mock_exercises = [
            {"name": "Fingerboard Max Hangs", "type": "strength", "time_required": 30, "required_facilities": "fingerboard"},
            {"name": "Boulder 4x4s", "type": "anaerobic_capacity", "time_required": 60, "required_facilities": "bouldering_wall"},
            {"name": "Continuous Low-Intensity Climbing", "type": "aerobic_capacity", "time_required": 45, "required_facilities": "bouldering_wall"},
            {"name": "Campus Board Exercises", "type": "power", "time_required": 30, "required_facilities": "campus_board"},
            {"name": "Route Intervals", "type": "anaerobic_power", "time_required": 60, "required_facilities": "lead_wall"},
            {"name": "ARC Training", "type": "aerobic_power", "time_required": 40, "required_facilities": "bouldering_wall"},
        ]
        
        test_data = PhasePlanRequest(
            route="Test Route",
            grade="7b",
            crag="Test Crag",
            weeks_to_train="8",
            sessions_per_week="4",
            time_per_session="2 hours",
            current_climbing_grade="7a",
            max_boulder_grade="V6",
            training_experience="3 years",
            training_facilities="Bouldering wall, Fingerboard, Campus board",
            age=25,
            route_angles="Overhanging",
            route_lengths="Long",
            hold_types="Crimpy",
            route_description="",
            perceived_strengths="",
            perceived_weaknesses="Endurance",
            attribute_ratings="",
            injury_history="None",
            general_fitness="Good",
            height="",
            weight="",
            preferred_climbing_style="",
            indoor_vs_outdoor="",
            onsight_flash_level="",
            redpointing_experience="",
            sleep_recovery="",
            work_life_balance="",
            fear_factors="",
            mindfulness_practices="",
            motivation_level="",
            access_to_coaches="",
            time_for_cross_training="",
            additional_notes=""
        )
        
        route_features = {"is_endurance": True, "is_crimpy": True}
        
        # Test filtering for different phases
        for phase_type in ["base", "peak", "taper"]:
            try:
                filtered = service.filter_exercises_enhanced(
                    mock_exercises,
                    test_data,
                    route_features,
                    phase_type=phase_type,
                    phase_weeks=4
                )
                
                exercise_names = [ex['name'] for ex in filtered]
                exercise_types = [ex['type'] for ex in filtered]
                
                details = f"{phase_type} phase: {len(filtered)} exercises - Types: {set(exercise_types)}"
                self.log_result("exercise_filtering", f"Filter for {phase_type} phase", True, details)
                
                # Phase-specific checks
                if phase_type == "base" and any("strength" in t for t in exercise_types):
                    self.log_result("exercise_filtering", f"{phase_type} includes strength", True)
                elif phase_type == "peak" and any("power" in t for t in exercise_types):
                    self.log_result("exercise_filtering", f"{phase_type} includes power", True)
                
            except Exception as e:
                self.log_result("exercise_filtering", f"Filter for {phase_type} phase", False, str(e))
    
    def test_plan_generator_initialization(self):
        """Test that PlanGeneratorService has phase_structure attribute"""
        print("\n=== Testing PlanGeneratorService Initialization ===")
        
        try:
            # Set a dummy API key if not present
            if not os.getenv("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"
            
            service = PlanGeneratorService()
            
            # Check for required attributes
            has_phase_structure = hasattr(service, 'phase_structure')
            self.log_result("plan_generation", "Has phase_structure attribute", has_phase_structure)
            
            has_exercise_filter = hasattr(service, 'exercise_filter')
            self.log_result("plan_generation", "Has exercise_filter attribute", has_exercise_filter)
            
            # Check types
            if has_phase_structure:
                is_correct_type = isinstance(service.phase_structure, PhaseStructureService)
                self.log_result("plan_generation", "phase_structure is PhaseStructureService", is_correct_type)
            
            if has_exercise_filter:
                is_correct_type = isinstance(service.exercise_filter, ExerciseFilterService)
                self.log_result("plan_generation", "exercise_filter is ExerciseFilterService", is_correct_type)
                
        except Exception as e:
            self.log_result("plan_generation", "Service initialization", False, str(e))
            self.results["errors"].append({
                "test": "PlanGeneratorService init",
                "error": str(e),
                "type": type(e).__name__
            })
    
    def test_generate_full_plan_method(self):
        """Test that generate_full_plan uses new phase-based approach"""
        print("\n=== Testing generate_full_plan Method ===")
        
        try:
            if not os.getenv("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"
            
            service = PlanGeneratorService()
            
            # Check if method exists
            has_method = hasattr(service, 'generate_full_plan')
            self.log_result("plan_generation", "Has generate_full_plan method", has_method)
            
            # Check for new helper methods
            has_phase_prompt = hasattr(service, '_create_phase_specific_prompt')
            self.log_result("plan_generation", "Has _create_phase_specific_prompt method", has_phase_prompt)
            
            has_validate_phase = hasattr(service, '_validate_phase_exercises')
            self.log_result("plan_generation", "Has _validate_phase_exercises method", has_validate_phase)
            
            # Check if the method signature looks correct
            if has_method:
                import inspect
                sig = inspect.signature(service.generate_full_plan)
                params = list(sig.parameters.keys())
                
                has_request_param = 'request' in params
                has_progress_param = 'on_progress' in params
                
                self.log_result("plan_generation", "Correct method signature", 
                              has_request_param and has_progress_param,
                              f"Parameters: {params}")
                
        except Exception as e:
            self.log_result("plan_generation", "Method inspection", False, str(e))
    
    def generate_summary(self):
        """Generate a summary of test results"""
        print("\n=== TEST SUMMARY ===")
        
        for category, results in self.results.items():
            if category == "errors":
                continue
                
            if results:
                passed = sum(1 for r in results if r['success'])
                total = len(results)
                print(f"\n{category.upper()}:")
                print(f"  Passed: {passed}/{total}")
                
                # Show failed tests
                failed = [r for r in results if not r['success']]
                if failed:
                    print("  Failed tests:")
                    for f in failed:
                        print(f"    - {f['test']}: {f['details']}")
        
        if self.results["errors"]:
            print("\n❌ ERRORS ENCOUNTERED:")
            for error in self.results["errors"]:
                print(f"  - {error['test']}: {error['type']} - {error['error']}")
        
        # Recommendations
        print("\n📋 RECOMMENDATIONS:")
        
        # Check for missing phase_structure
        phase_init_failed = any(r['test'] == 'Has phase_structure attribute' and not r['success'] 
                               for r in self.results['plan_generation'])
        
        if phase_init_failed:
            print("""
  ⚠️  PlanGeneratorService is missing phase_structure attribute.
     Fix: In app/services/plan_generator.py, ensure:
     1. Add import: from services.phase_structure import PhaseStructureService
     2. In __init__, add: self.phase_structure = PhaseStructureService()
""")
        
        # Check for method issues
        method_issues = any(not r['success'] for r in self.results['plan_generation'] 
                           if 'method' in r['test'].lower())
        
        if method_issues:
            print("""
  ⚠️  New methods may not be properly implemented.
     Fix: Ensure generate_full_plan, _create_phase_specific_prompt, and 
          _validate_phase_exercises are all present in plan_generator.py
""")
        
        # Success message
        all_passed = all(r['success'] for category in ['phase_structure', 'exercise_filtering', 'plan_generation'] 
                        for r in self.results[category])
        
        if all_passed and not self.results["errors"]:
            print("""
  ✅ All tests passed! The refactored system appears to be working correctly.
     Next steps:
     1. Run a full integration test with a real API key
     2. Generate a sample plan and verify phases are structured correctly
     3. Check that exercises vary appropriately between phases
""")

def main():
    """Run all tests"""
    print("🧗 Testing Phase-Based Plan Generator Refactoring")
    print("=" * 50)
    
    tester = PlanGeneratorTester()
    
    # Run tests
    tester.test_phase_structure_service()
    tester.test_exercise_filtering()
    tester.test_plan_generator_initialization()
    tester.test_generate_full_plan_method()
    
    # Generate summary
    tester.generate_summary()

if __name__ == "__main__":
    main()
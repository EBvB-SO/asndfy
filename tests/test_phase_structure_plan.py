# test_phase_structure_plan.py
"""
Test script for phase structure service
Run from backend directory: python test_phase_structure_plan.py
"""

import os
import sys
import time
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("\n=== Testing Phase Structure Service ===\n")

def test_phase_structure_service():
    """Test the phase structure service independently"""
    print("\n\n📊 Testing Phase Structure Service")
    print("=" * 60)
    
    try:
        from app.services.phase_structure import PhaseStructureService
        from app.services.exercise_filter import ExerciseFilterService
        from app.models.training_plan import PhasePlanRequest
        
        # Create services
        phase_service = PhaseStructureService()
        exercise_filter = ExerciseFilterService()
        
        # Create test data for La Creme
        plan_data = PhasePlanRequest(
            route="La Creme",
            grade="7c+",
            crag="Anstey's Cove",
            route_angles="Vertical",
            route_lengths="Medium",
            hold_types="Crimpy, Slopers",
            route_description="Route on crimps and slopers with a tough V8 crux in the middle",
            current_climbing_grade="7a+",
            max_boulder_grade="V6",
            training_experience="3 years",
            years_experience=3,
            perceived_strengths="Endurance, Mental game, Slopers",
            perceived_weaknesses="Crimp strength, Power, Dynamic moves",
            attribute_ratings="Endurance:4, Power:2, Crimp Strength:2, Technique:3, Mental:4",
            weeks_to_train="8",
            sessions_per_week="4",
            time_per_session="2 hours",
            training_facilities="bouldering_wall, lead_wall, fingerboard, campus_board, weights",
            injury_history="Minor finger tweak 6 months ago, fully recovered",
            general_fitness="Good",
            height="175",
            weight="70",
            age=28,
            preferred_climbing_style="Sport climbing",
            indoor_vs_outdoor="Both",
            onsight_flash_level="7a",
            redpointing_experience="Up to 7b+",
            sleep_recovery="Good",
            work_life_balance="Balanced",
            fear_factors="Some fear of falling",
            mindfulness_practices="Some meditation",
            motivation_level="High",
            access_to_coaches="No",
            time_for_cross_training="1 hour",
            additional_notes="Want to send La Creme before season ends"
        )
        
        # Test for different plan lengths
        test_cases = [
            (4, "Short plan"),
            (6, "Medium-short plan"),
            (8, "Medium plan"),
            (12, "Long plan"),
            (16, "Very long plan")
        ]
        
        for weeks, description in test_cases:
            print(f"\n🔍 Testing {description} ({weeks} weeks):")
            
            # Get route features
            from app.services.plan_generator import PlanGeneratorService
            gen_service = PlanGeneratorService()
            route_features = gen_service.analyze_route(
                plan_data.route, 
                plan_data.grade, 
                plan_data.crag, 
                user_data=plan_data
            )
            
            # Get attribute ratings
            attribute_ratings = exercise_filter.parse_attribute_ratings(plan_data.attribute_ratings)
            
            # Determine phases
            phases = phase_service.determine_phase_structure(
                plan_data,
                weeks,
                int(plan_data.sessions_per_week),
                route_features,
                attribute_ratings
            )
            
            print(f"  Total phases: {len(phases)}")
            total_weeks = sum(p['weeks'] for p in phases)
            print(f"  Total weeks covered: {total_weeks} (expected: {weeks})")
            
            for i, phase in enumerate(phases):
                print(f"  Phase {i+1}: {phase['name']}")
                print(f"    - Type: {phase['type']}")
                print(f"    - Weeks: {phase['weeks']}")
                print(f"    - Focus: {phase['description'][:60]}...")
            
            # Verify weeks add up
            if total_weeks != weeks:
                print(f"  ⚠️  WARNING: Phase weeks don't add up! {total_weeks} != {weeks}")
            else:
                print(f"  ✅ Phase weeks correctly sum to {weeks}")
        
        # Test edge cases
        print("\n\n🔍 Testing Edge Cases:")
        
        # Test 1: Pure endurance climber on endurance route
        print("\n1. Strong climber on endurance route:")
        endurance_data = plan_data.copy()
        endurance_data.perceived_strengths = "Strength, Power, Crimps"
        endurance_data.perceived_weaknesses = "Endurance, Stamina"
        endurance_data.attribute_ratings = "Endurance:2, Power:5, Crimp Strength:5"
        endurance_data.route_lengths = "Long"
        endurance_data.route_description = "80m sustained pump fest"
        
        route_features = {"is_endurance": True, "is_power": False, "is_steep": False}
        attribute_ratings = {"endurance": 2, "power": 5, "crimp_strength": 5}
        
        phases = phase_service.determine_phase_structure(
            endurance_data, 8, 4, route_features, attribute_ratings
        )
        
        print(f"  Phases: {[p['name'] for p in phases]}")
        print(f"  Phase types: {[p['type'] for p in phases]}")
        
        # Test 2: Beginner climber
        print("\n2. Beginner climber (6 months experience):")
        beginner_data = plan_data.copy()
        beginner_data.training_experience = "6 months"
        beginner_data.years_experience = 0.5
        beginner_data.max_boulder_grade = "V2"
        beginner_data.current_climbing_grade = "6a"
        
        phases = phase_service.determine_phase_structure(
            beginner_data, 6, 3, route_features, attribute_ratings
        )
        
        print(f"  Phases: {[p['name'] for p in phases]}")
        
        print("\n✅ Phase Structure Service tests complete!")
        
    except Exception as e:
        print(f"❌ Phase structure test failed: {e}")
        import traceback
        traceback.print_exc()

def test_exercise_filtering_per_phase():
    """Test that exercise filtering works differently per phase"""
    print("\n\n🏋️ Testing Phase-Specific Exercise Filtering")
    print("=" * 60)
    
    try:
        from app.services.exercise_filter import ExerciseFilterService
        from app.services.plan_generator import PlanGeneratorService
        from app.models.training_plan import PhasePlanRequest
        from app.db.db_access import get_exercises
        
        # Create services
        filter_service = ExerciseFilterService()
        gen_service = PlanGeneratorService()
        
        # Create test data
        plan_data = PhasePlanRequest(
            route="Test Route",
            grade="7c",
            crag="Test Crag",
            route_angles="Overhanging",
            route_lengths="Short",
            hold_types="Crimpy",
            route_description="Short powerful route",
            current_climbing_grade="7a",
            max_boulder_grade="V5",
            training_experience="2 years",
            years_experience=2,
            perceived_strengths="Endurance",
            perceived_weaknesses="Power, Crimps",
            attribute_ratings="Power:2, Endurance:4, Crimp Strength:2",
            weeks_to_train="8",
            sessions_per_week="3",
            time_per_session="2 hours",
            training_facilities="bouldering_wall, fingerboard, campus_board",
            injury_history="None",
            general_fitness="Good",
            height="170",
            weight="65",
            age=25,
            preferred_climbing_style="Sport",
            indoor_vs_outdoor="Both",
            onsight_flash_level="6c+",
            redpointing_experience="Some",
            sleep_recovery="Good",
            work_life_balance="Good",
            fear_factors="None",
            mindfulness_practices="None",
            motivation_level="High",
            access_to_coaches="No",
            time_for_cross_training="30 min",
            additional_notes=""
        )
        
        # Get exercises and route features
        all_exercises = get_exercises()
        route_features = gen_service.analyze_route(
            plan_data.route, 
            plan_data.grade, 
            plan_data.crag, 
            user_data=plan_data
        )
        
        print(f"Total exercises available: {len(all_exercises)}")
        print(f"Route features: power={route_features.get('is_power')}, endurance={route_features.get('is_endurance')}")
        
        # Test filtering for different phases
        phase_types = ["base", "peak", "taper"]
        
        for phase_type in phase_types:
            print(f"\n🔍 Filtering for '{phase_type}' phase:")
            
            filtered = filter_service.filter_exercises_enhanced(
                all_exercises,
                plan_data,
                route_features,
                phase_type=phase_type,
                phase_weeks=4
            )
            
            print(f"  Exercises after filtering: {len(filtered)}")
            
            # Show top exercises by type
            by_type = {}
            for ex in filtered[:10]:
                ex_type = ex.get('type', 'unknown')
                if ex_type not in by_type:
                    by_type[ex_type] = []
                by_type[ex_type].append(ex['name'])
            
            print(f"  Top exercises by type:")
            for ex_type, names in by_type.items():
                print(f"    {ex_type}: {', '.join(names[:3])}")
            
            # Check phase-specific patterns
            if phase_type == "base":
                strength_count = sum(1 for ex in filtered if ex['type'] == 'strength')
                print(f"  Strength exercises: {strength_count} (should be high)")
            elif phase_type == "peak":
                power_endurance_count = sum(1 for ex in filtered if 'power' in ex['type'])
                print(f"  Power-endurance exercises: {power_endurance_count} (should be high)")
            elif phase_type == "taper":
                total_score = sum(ex.get('score', 0) for ex in filtered)
                print(f"  Average score: {total_score/len(filtered):.1f} (should be lower)")
        
        print("\n✅ Phase-specific filtering tests complete!")
        
    except Exception as e:
        print(f"❌ Exercise filtering test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test 1: Phase structure service alone
    test_phase_structure_service()
    
    # Test 2: Exercise filtering per phase
    test_exercise_filtering_per_phase()
    
    print("\n\n=== All Tests Complete ===\n")
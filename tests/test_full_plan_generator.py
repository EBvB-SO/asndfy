#test_full_plan_generator.py

"""
Test script for FULL plan generator with realistic facility filtering
Run from backend directory: python test_full_plan_generator.py
"""

import os
import sys
import time
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load env vars BEFORE importing anything from app
from dotenv import load_dotenv
load_dotenv()

print("\n=== Testing Full Plan Generator ===\n")

# Check environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not set!")
    sys.exit(1)
else:
    print(f"✅ API key found: {api_key[:10]}...")

def test_full_plan():
    """Test the full plan generation for La Creme with realistic facilities"""
    
    try:
        from app.services.plan_generator import PlanGeneratorService
        from app.models.training_plan import PhasePlanRequest, FullPlanRequest
        from app.db.db_access import get_exercises
        
        print("\n✅ Modules imported successfully")
        
        # Create service
        print("\n🔧 Creating PlanGeneratorService...")
        start = time.time()
        service = PlanGeneratorService()
        print(f"✅ Service created in {time.time() - start:.2f}s")
        
        # Create the base request for La Creme
        print("\n📝 Creating plan request for La Creme...")
        plan_data = PhasePlanRequest(
            # Route details
            route="La Creme",
            grade="7c+",
            crag="Anstey's Cove",
            route_angles="Vertical",
            route_lengths="Medium",
            hold_types="Crimpy, Slopers",
            route_description="Route on crimps and slopers with a tough V8 crux in the middle",
            
            # Climber profile
            current_climbing_grade="7a+",
            max_boulder_grade="V6",
            training_experience="3 years",
            perceived_strengths="Endurance, Mental game, Slopers",
            perceived_weaknesses="Crimp strength, Power, Dynamic moves",
            attribute_ratings="Endurance:4, Power:2, Crimp Strength:2, Technique:3, Mental:4",
            
            # Training parameters
            weeks_to_train="8",
            sessions_per_week="4",
            time_per_session="2 hours",
            
            # REALISTIC facilities - what most climbers actually have access to
            training_facilities="bouldering_wall, lead_wall, fingerboard, campus_board, weights",
            
            # Physical profile
            injury_history="Minor finger tweak 6 months ago, fully recovered",
            general_fitness="Good",
            height="175",
            weight="70",
            age="28",
            
            # Additional info
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
        
        # Show exercise filtering
        print("\n🏋️ Testing exercise filtering with realistic facilities...")
        all_exercises = get_exercises()
        print(f"  Total exercises in database: {len(all_exercises)}")
        
        # Get route features for filtering
        route_features = service.analyze_route(
            plan_data.route, 
            plan_data.grade, 
            plan_data.crag, 
            user_data=plan_data
        )
        
        # Filter exercises
        filtered = service.exercise_filter.filter_exercises_enhanced(
            all_exercises, plan_data, route_features
        )
        print(f"  Exercises after filtering: {len(filtered)}")
        print(f"  Filtered out: {len(all_exercises) - len(filtered)} exercises")
        
        print("\n  Top 10 exercises by relevance:")
        for i, ex in enumerate(filtered[:10]):
            print(f"    {i+1}. {ex['name']} (score: {ex.get('score', 0)}, time: {ex.get('time_required', '?')} min)")
        
        # Create full plan request
        full_request = FullPlanRequest(
            plan_data=plan_data,
            weeks_to_train=8,
            sessions_per_week=4,
            previous_analysis=None
        )
        
        print("\n✅ Request created")
        print(f"\n📊 Plan parameters:")
        print(f"  - Total weeks: {full_request.weeks_to_train}")
        print(f"  - Sessions per week: {full_request.sessions_per_week}")
        print(f"  - Total sessions: {full_request.weeks_to_train * full_request.sessions_per_week}")
        print(f"  - Available facilities: {plan_data.training_facilities}")
        
        # First get the preview (which we know works)
        print("\n📄 Generating preview first...")
        preview_start = time.time()
        preview = service.generate_preview(plan_data)
        preview_time = time.time() - preview_start
        print(f"✅ Preview generated in {preview_time:.2f}s")
        
        # Now generate the FULL plan
        print("\n\n🚀 Generating FULL training plan...")
        print("⏱️  This may take 30-60 seconds...")
        
        # Progress callback
        def on_progress(current, total):
            print(f"  📊 Progress: Phase {current}/{total}")
        
        start = time.time()
        try:
            # Generate with progress updates
            full_plan = service.generate_full_plan(full_request, on_progress=on_progress)
            elapsed = time.time() - start
            
            print(f"\n✅ FULL PLAN GENERATED in {elapsed:.2f} seconds!")
            
            # Analyze the plan structure
            if "phases" in full_plan:
                phases = full_plan["phases"]
                print(f"\n📋 Plan Structure:")
                print(f"  - Total phases: {len(phases)}")
                
                # Track exercise usage
                exercise_usage = {}
                
                for i, phase in enumerate(phases):
                    print(f"\n  Phase {i+1}: {phase.get('phase_name', 'Unnamed')}")
                    print(f"    Description: {phase.get('description', '')[:100]}...")
                    
                    schedule = phase.get('weekly_schedule', [])
                    print(f"    Days per week: {len(schedule)}")
                    
                    # Analyze exercises in this phase
                    for day in schedule:
                        focus = day.get('focus', '')
                        exercises = [ex.strip() for ex in focus.split('+')]
                        for ex in exercises:
                            if ex:
                                exercise_usage[ex] = exercise_usage.get(ex, 0) + 1
                    
                    # Show first day as example
                    if schedule:
                        day1 = schedule[0]
                        print(f"    Example - {day1.get('day')}:")
                        print(f"      Focus: {day1.get('focus')}")
                        print(f"      Details preview: {day1.get('details', '')[:150]}...")
                
                # Show exercise usage stats
                print(f"\n📊 Exercise Usage Statistics:")
                print(f"  Total unique exercises: {len(exercise_usage)}")
                print("\n  Most used exercises:")
                sorted_exercises = sorted(exercise_usage.items(), key=lambda x: x[1], reverse=True)
                for ex, count in sorted_exercises[:10]:
                    print(f"    - {ex}: {count} sessions")
                
                # Check if any exercises require unavailable facilities
                print("\n🔍 Verifying all exercises can be performed with available facilities...")
                available_facilities = set(plan_data.training_facilities.split(", "))
                issues = []
                
                for ex_name in exercise_usage.keys():
                    # Find this exercise in the original list
                    for original_ex in all_exercises:
                        if original_ex['name'] == ex_name:
                            required = set(original_ex.get('required_facilities', 'bouldering_wall').split(","))
                            if not required.issubset(available_facilities):
                                missing = required - available_facilities
                                issues.append(f"{ex_name} needs: {', '.join(missing)}")
                                break
                
                if issues:
                    print("  ⚠️  Found exercises requiring unavailable facilities:")
                    for issue in issues:
                        print(f"    - {issue}")
                else:
                    print("  ✅ All exercises can be performed with available facilities!")
                
                # Save the plan to a file for inspection
                output_file = "test_full_plan_output.json"
                with open(output_file, 'w') as f:
                    json.dump(full_plan, f, indent=2)
                print(f"\n💾 Full plan saved to: {output_file}")
                
            else:
                print("\n❌ No phases found in plan!")
                print(f"Plan keys: {list(full_plan.keys())}")
            
        except Exception as e:
            elapsed = time.time() - start
            print(f"\n❌ Full plan generation FAILED after {elapsed:.2f} seconds!")
            print(f"Error type: {type(e).__name__}")
            print(f"Error: {str(e)}")
            
            if "timeout" in str(e).lower():
                print("\n💡 Timeout suggestions:")
                print("  1. Try reducing weeks from 8 to 6")
                print("  2. Try reducing sessions from 4 to 3")
                print("  3. Add request_timeout=120 to the OpenAI call")
            
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def test_minimal_facilities():
    """Test with minimal facilities to see extreme filtering"""
    print("\n\n=== Testing with Minimal Facilities ===\n")
    
    try:
        from app.services.plan_generator import PlanGeneratorService
        from app.models.training_plan import PhasePlanRequest, FullPlanRequest
        from app.db.db_access import get_exercises
        
        service = PlanGeneratorService()
        
        # Request with very limited facilities
        plan_data = PhasePlanRequest(
            route="Test Route",
            grade="7a",
            crag="Test Crag",
            route_angles="Vertical",
            route_lengths="Short",
            hold_types="Crimpy",
            route_description="Simple test route",
            
            current_climbing_grade="6c+",
            max_boulder_grade="V4",
            training_experience="2 years",
            perceived_strengths="Endurance",
            perceived_weaknesses="Power",
            attribute_ratings="",
            
            weeks_to_train="4",
            sessions_per_week="3",
            time_per_session="1.5 hours",
            
            # VERY LIMITED facilities
            training_facilities="bouldering_wall, fingerboard",  # No campus, no weights, etc.
            
            injury_history="None",
            general_fitness="Good",
            height="170",
            weight="65",
            age="25",
            preferred_climbing_style="Sport",
            indoor_vs_outdoor="Indoor",
            onsight_flash_level="6b+",
            redpointing_experience="Some",
            sleep_recovery="Good",
            work_life_balance="Good",
            fear_factors="None",
            mindfulness_practices="None",
            motivation_level="High",
            access_to_coaches="No",
            time_for_cross_training="None",
            additional_notes=""
        )
        
        # Show filtering results
        all_exercises = get_exercises()
        route_features = service.analyze_route(plan_data.route, plan_data.grade, plan_data.crag, plan_data)
        filtered = service.exercise_filter.filter_exercises_enhanced(all_exercises, plan_data, route_features)
        
        print(f"With only bouldering_wall + fingerboard:")
        print(f"  - Started with: {len(all_exercises)} exercises")
        print(f"  - After filtering: {len(filtered)} exercises")
        print(f"  - Removed: {len(all_exercises) - len(filtered)} exercises ({(len(all_exercises) - len(filtered))/len(all_exercises)*100:.1f}%)")
        
        if filtered:
            print("\n  Available exercises:")
            for i, ex in enumerate(filtered[:10]):
                print(f"    {i+1}. {ex['name']}")
                
    except Exception as e:
        print(f"❌ Minimal facilities test error: {e}")

if __name__ == "__main__":
    # Test the full plan generator with realistic facilities
    test_full_plan()
    
    # Also test with minimal facilities to show filtering
    test_minimal_facilities()
    
    print("\n\n=== All Tests Complete ===\n")
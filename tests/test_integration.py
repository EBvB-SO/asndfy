#app/tests/test_integration.py
"""
Integration test for full plan generation.
This script tests the complete flow from request to generated plan.
"""
import os
import sys
import json
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.training_plan import PhasePlanRequest, FullPlanRequest
from app.services.plan_generator import PlanGeneratorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_request(weeks=8, sessions=4):
    """Create a test request for plan generation"""
    plan_data = PhasePlanRequest(
        route="The Shield",
        grade="7b+",
        crag="El Capitan",
        route_angles="Overhanging, Roof",
        route_lengths="Long",
        hold_types="Crimpy, Pinches",
        route_description="Sustained overhanging climbing with a powerful crux through a roof section. Requires both endurance for the long approach and power for the crux.",
        weeks_to_train=str(weeks),
        sessions_per_week=str(sessions),
        time_per_session="2 hours",
        current_climbing_grade="7a",
        max_boulder_grade="V5",
        training_experience="3 years",
        years_experience=3.0,
        age=28,
        perceived_strengths="Power, Core strength",
        perceived_weaknesses="Endurance, Finger strength",
        attribute_ratings="finger_strength:2, endurance:2, power:4, power_endurance:3, technique:3",
        training_facilities="Bouldering wall, Lead wall, Fingerboard, Campus board, Weights",
        injury_history="Minor finger tweaks in the past, fully recovered",
        general_fitness="Good",
        height="175cm",
        weight="70kg",
        preferred_climbing_style="Sport climbing",
        indoor_vs_outdoor="Both",
        onsight_flash_level="6c+",
        redpointing_experience="Yes, have redpointed up to 7a+",
        sleep_recovery="Good",
        work_life_balance="Balanced",
        fear_factors="Some fear on runouts",
        mindfulness_practices="Regular meditation",
        motivation_level="High",
        access_to_coaches="No",
        time_for_cross_training="Yes",
        additional_notes="Really motivated to send this route!"
    )
    
    return FullPlanRequest(
        plan_data=plan_data,
        weeks_to_train=weeks,
        sessions_per_week=sessions,
        previous_analysis=None
    )

def test_mock_generation():
    """Test plan generation with mocked OpenAI responses"""
    print("\n🧪 Testing Plan Generation (Mock Mode)")
    print("=" * 50)
    
    # Mock the OpenAI response
    import openai
    
    def mock_create(*args, **kwargs):
        """Mock OpenAI response"""
        # Extract the prompt to determine which phase we're generating
        messages = kwargs.get('messages', [])
        user_message = messages[-1]['content'] if messages else ""
        
        if "BASE phase" in user_message or "Strength" in user_message:
            response_content = {
                "weekly_schedule": [
                    {
                        "day": "Monday",
                        "focus": "Fingerboard Max Hangs + Core Circuit",
                        "details": "Warm-up: 15 min progressive climbing. Main: Fingerboard max hangs - 5 sets x 10 seconds on 18mm edge at 85% effort, 3 min rest. Core: 3 rounds of hanging knee raises, planks, and Russian twists. Cool-down: 5 min easy climbing."
                    },
                    {
                        "day": "Wednesday",
                        "focus": "Boulder 4x4s",
                        "details": "Warm-up: 15 min progressive bouldering. Main: 4 sets of 4 boulder problems at 80% difficulty, 3 min rest between sets. Focus on powerful moves. Cool-down: 10 min easy climbing."
                    },
                    {
                        "day": "Friday",
                        "focus": "Max Boulder Sessions",
                        "details": "Warm-up: 20 min progressive bouldering. Main: Work on 3-5 boulder problems at 90-95% difficulty. Take full rest between attempts. Session time: 90 minutes total."
                    },
                    {
                        "day": "Sunday",
                        "focus": "Continuous Low-Intensity Climbing",
                        "details": "Warm-up: 10 min easy climbing. Main: 45 minutes of continuous climbing at 60-70% difficulty. Focus on movement quality and breathing. Cool-down: 5 min stretching."
                    }
                ]
            }
        else:  # PEAK phase
            response_content = {
                "weekly_schedule": [
                    {
                        "day": "Monday",
                        "focus": "Route Intervals",
                        "details": "Warm-up: 15 min progressive climbing. Main: 5 x 4-minute intervals at 85% effort with 4 min rest. Simulate route pacing. Cool-down: 10 min easy climbing."
                    },
                    {
                        "day": "Tuesday",
                        "focus": "Fingerboard Repeater Blocks",
                        "details": "Warm-up: 10 min general. Main: 3 sets of 7 seconds on, 3 seconds off x 6 reps on 20mm edge. 3 min rest between sets. Cool-down: Antagonist exercises."
                    },
                    {
                        "day": "Thursday",
                        "focus": "Linked Bouldering Circuits",
                        "details": "Warm-up: 15 min. Main: 3 circuits of 6 boulder problems with minimal rest. 5 min rest between circuits. Focus on maintaining power. Cool-down: 10 min easy."
                    },
                    {
                        "day": "Saturday",
                        "focus": "Mixed Intensity Laps",
                        "details": "Warm-up: 15 min. Main: Alternating hard (90%) and moderate (70%) routes. 6-8 routes total. Focus on recovery between hard efforts."
                    }
                ]
            }
        
        class MockResponse:
            class Choice:
                class Message:
                    content = json.dumps(response_content)
                message = Message()
            choices = [Choice()]
        
        return MockResponse()
    
    # Temporarily replace the OpenAI method
    original_create = openai.ChatCompletion.create
    openai.ChatCompletion.create = mock_create
    
    try:
        # Test the plan generator
        generator = PlanGeneratorService()
        
        # Progress tracking
        progress_updates = []
        def track_progress(current, total):
            progress_updates.append((current, total))
            print(f"  Progress: Phase {current}/{total}")
        
        # Generate plans of different lengths
        test_configs = [
            (4, 3, "Short plan"),
            (8, 4, "Medium plan"),
            (12, 4, "Long plan")
        ]
        
        for weeks, sessions, desc in test_configs:
            print(f"\n📊 Testing {desc}: {weeks} weeks, {sessions} sessions/week")
            
            try:
                request = create_test_request(weeks, sessions)
                progress_updates.clear()
                
                # Generate the plan
                plan = generator.generate_full_plan(request, on_progress=track_progress)
                
                # Analyze results
                print(f"\n✅ Plan generated successfully!")
                print(f"  - Phases: {len(plan.get('phases', []))}")
                
                for i, phase in enumerate(plan.get('phases', [])):
                    days = len(phase.get('weekly_schedule', []))
                    print(f"  - Phase {i+1}: {phase.get('phase_name', 'Unknown')} ({days} days/week)")
                    
                    # Check exercise variety
                    exercises = set()
                    for day in phase.get('weekly_schedule', []):
                        focus = day.get('focus', '')
                        for ex in focus.split('+'):
                            exercises.add(ex.strip())
                    
                    print(f"    Unique exercises: {len(exercises)}")
                    print(f"    Exercises: {', '.join(sorted(exercises))}")
                
                # Verify progress tracking
                print(f"\n  Progress updates: {progress_updates}")
                
            except Exception as e:
                print(f"\n❌ Error generating {desc}: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
    
    finally:
        # Restore original method
        openai.ChatCompletion.create = original_create
    
    print("\n" + "=" * 50)
    print("Mock testing complete!")

def test_real_generation():
    """Test with real API if key is available"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "dummy-key-for-testing":
        print("\n⚠️  No real OpenAI API key found. Skipping real generation test.")
        print("   To test real generation, set OPENAI_API_KEY in your environment.")
        return
    
    print("\n🚀 Testing Plan Generation (Real API)")
    print("=" * 50)
    
    try:
        generator = PlanGeneratorService()
        request = create_test_request(weeks=6, sessions=3)
        
        print("Generating a 6-week plan...")
        
        # Track progress
        def show_progress(current, total):
            print(f"  Generating phase {current}/{total}...")
        
        start_time = datetime.now()
        plan = generator.generate_full_plan(request, on_progress=show_progress)
        end_time = datetime.now()
        
        print(f"\n✅ Plan generated in {(end_time - start_time).total_seconds():.1f} seconds")
        
        # Save to file
        output_file = f"test_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        print(f"📁 Plan saved to: {output_file}")
        
        # Quick analysis
        total_exercises = set()
        for phase in plan.get('phases', []):
            for day in phase.get('weekly_schedule', []):
                focus = day.get('focus', '')
                for ex in focus.split('+'):
                    total_exercises.add(ex.strip())
        
        print(f"\nPlan Analysis:")
        print(f"  - Total phases: {len(plan.get('phases', []))}")
        print(f"  - Unique exercises used: {len(total_exercises)}")
        print(f"  - Exercise variety: {', '.join(sorted(total_exercises))}")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Run integration tests"""
    print("🧗 Integration Test for Phase-Based Plan Generator")
    print("=" * 50)
    
    # Test with mocked responses first
    test_mock_generation()
    
    # Test with real API if available
    test_real_generation()
    
    print("\n✅ Integration testing complete!")
    print("\nNext steps:")
    print("1. Review any errors in the test output")
    print("2. Check that phases follow expected patterns")
    print("3. Verify exercises change between phases")
    print("4. Ensure total weeks match requested duration")

if __name__ == "__main__":
    main()
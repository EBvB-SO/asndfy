#test_preview_generator.py
"""
Test script for preview generator
Run this from the project root directory: python test_preview_generator.py
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_preview_generator():
    """Test the preview generator with La Creme route"""
    
    print("\n=== Testing Preview Generator ===\n")
    
    # Check if OpenAI API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables!")
        print("Please ensure your .env file contains: OPENAI_API_KEY=your-key-here")
        return
    else:
        print(f"✅ OpenAI API key found (starts with: {api_key[:10]}...)")
    
    try:
        # Import the necessary modules
        from app.services.plan_generator import PlanGeneratorService
        from app.models.training_plan import PhasePlanRequest
        
        print("\n✅ Successfully imported required modules")
        
        # Create the plan generator service
        print("\n🔧 Creating PlanGeneratorService...")
        start_time = time.time()
        plan_generator = PlanGeneratorService()
        print(f"✅ Service created in {time.time() - start_time:.2f} seconds")
        
        # Create a test request for La Creme
        print("\n📝 Creating test request for La Creme...")
        test_request = PhasePlanRequest(
            # Route details
            route="La Creme",
            grade="7c+",
            crag="Anstey's Cove",
            route_angles="Vertical",
            route_lengths="Medium",
            hold_types="Crimpy, Slopers",
            route_description="Route on crimps and slopers with a tough V8 crux in the middle",
            
            # Climber profile - intermediate climber with good endurance but weak on crimps
            current_climbing_grade="7a+",
            max_boulder_grade="V6",
            training_experience="3 years of structured training",
            perceived_strengths="Endurance, Mental game, Slopers",
            perceived_weaknesses="Crimp strength, Power, Dynamic moves",
            attribute_ratings="Endurance:4, Power:2, Crimp Strength:2, Technique:3, Mental:4",
            
            # Training parameters
            weeks_to_train="8",
            sessions_per_week="4",
            time_per_session="2 hours",
            
            # Available facilities
            training_facilities="bouldering_wall, lead_wall, fingerboard, campus_board, weights",
            
            # Physical profile
            injury_history="Minor finger tweak 6 months ago, fully recovered",
            general_fitness="Good",
            height="175cm",
            weight="70kg",
            age="28",
            
            # Additional climbing info
            preferred_climbing_style="Sport climbing, some bouldering",
            indoor_vs_outdoor="Both, prefer outdoor",
            onsight_flash_level="7a",
            redpointing_experience="Have redpointed up to 7b+",
            
            # Lifestyle factors
            sleep_recovery="Good - 7-8 hours per night",
            work_life_balance="Balanced - office job with flexible hours",
            fear_factors="Some fear of falling on lead",
            mindfulness_practices="Occasional meditation",
            motivation_level="High",
            access_to_coaches="No regular coach",
            time_for_cross_training="1 hour per week",
            additional_notes="Really motivated to send La Creme before end of season"
        )
        
        print("✅ Test request created")
        print(f"\n📊 Request details:")
        print(f"  - Route: {test_request.route} ({test_request.grade}) at {test_request.crag}")
        print(f"  - Climber: {test_request.current_climbing_grade} sport, {test_request.max_boulder_grade} boulder")
        print(f"  - Training: {test_request.weeks_to_train} weeks, {test_request.sessions_per_week} sessions/week")
        
        # Test route analysis first
        print("\n🔍 Testing route analysis...")
        start_time = time.time()
        route_features = plan_generator.analyze_route(
            test_request.route,
            test_request.grade,
            test_request.crag,
            user_data=test_request
        )
        analysis_time = time.time() - start_time
        
        print(f"✅ Route analysis completed in {analysis_time:.2f} seconds")
        print(f"\n📋 Route features detected:")
        for key, value in route_features.items():
            if key != "key_challenges":
                print(f"  - {key}: {value}")
        print(f"  - key_challenges: {', '.join(route_features['key_challenges'])}")
        
        # Now test the preview generation
        print("\n🚀 Generating preview...")
        print("⏱️  Starting timer...")
        
        start_time = time.time()
        try:
            preview = plan_generator.generate_preview(test_request)
            generation_time = time.time() - start_time
            
            print(f"\n✅ Preview generated successfully in {generation_time:.2f} seconds!")
            
            print("\n📄 Route Overview:")
            print("-" * 50)
            print(preview.get("route_overview", "No overview generated"))
            
            print("\n📄 Training Approach:")
            print("-" * 50)
            print(preview.get("training_approach", "No approach generated"))
            
            # Check if response is complete
            if not preview.get("route_overview") or not preview.get("training_approach"):
                print("\n⚠️  WARNING: Preview is incomplete!")
            
        except Exception as e:
            generation_time = time.time() - start_time
            print(f"\n❌ Preview generation failed after {generation_time:.2f} seconds!")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            
            # More detailed error info
            import traceback
            print("\n📋 Full traceback:")
            traceback.print_exc()
            
            # Check if it's a timeout
            if "timeout" in str(e).lower():
                print("\n💡 This appears to be a timeout issue. Possible causes:")
                print("  1. Slow internet connection")
                print("  2. OpenAI API is slow/overloaded")
                print("  3. The prompt is too complex")
                print("  4. Network firewall blocking the request")
        
        # Test the exercise filtering too
        print("\n\n🏋️ Testing exercise filtering...")
        try:
            from app.db.db_access import get_exercises
            exercises = get_exercises()
            print(f"✅ Found {len(exercises)} exercises in database")
            
            filtered = plan_generator.exercise_filter.filter_exercises_enhanced(
                exercises, test_request, route_features
            )
            print(f"✅ Filtered to {len(filtered)} relevant exercises")
            
            if filtered:
                print("\n📋 Top 15 exercises by relevance score:")
                for i, ex in enumerate(filtered[:15]):
                    print(f"  {i+1}. {ex['name']} (score: {ex.get('score', 0)}, time: {ex.get('time_required', '?')} min)")
        except Exception as e:
            print(f"❌ Exercise filtering failed: {e}")
            
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

def test_openai_directly():
    """Test OpenAI API directly to isolate connection issues"""
    print("\n\n=== Testing OpenAI API Directly ===\n")
    
    try:
        import openai
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ No API key found")
            return
            
        openai.api_key = api_key
        
        print("🔧 Testing simple OpenAI API call...")
        start_time = time.time()
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'API is working!' in exactly 3 words."}
            ],
            temperature=0,
            max_tokens=10,
            timeout=30  # 30 second timeout
        )
        
        api_time = time.time() - start_time
        result = response.choices[0].message.content.strip()
        
        print(f"✅ API responded in {api_time:.2f} seconds: '{result}'")
        
    except Exception as e:
        api_time = time.time() - start_time
        print(f"❌ OpenAI API test failed after {api_time:.2f} seconds: {e}")

if __name__ == "__main__":
    # Run the OpenAI direct test first
    test_openai_directly()
    
    # Then run the main preview generator test
    test_preview_generator()
    
    print("\n\n=== Test Complete ===\n")
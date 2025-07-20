# services/plan_generator.py
import json
import re
import logging
import openai
import os
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
import sys

# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.db.db_access as db

from app.models.training_plan import PhasePlanRequest, FullPlanRequest
from app.services.exercise_filter import ExerciseFilterService
from app.services.phase_structure import PhaseStructureService
from app.services.description_keywords import DESCRIPTION_KEYWORDS

logger = logging.getLogger(__name__)

class PlanGeneratorService:
    """Service for generating training plans using OpenAI"""
    
    def __init__(self):
        # Fail fast if the API key isn’t configured
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.error("Missing OPENAI_API_KEY environment variable.")
            raise EnvironmentError("Missing OPENAI_API_KEY environment variable.")

        # Configure OpenAI client
        openai.api_key = self.openai_api_key

        # Initialize auxiliary services
        self.exercise_filter = ExerciseFilterService()
        self.phase_structure = PhaseStructureService()
    
    def analyze_route(self, route_name: str, grade: str, crag: str, user_data: PhasePlanRequest = None) -> dict:
        """
        Extract climbing characteristics from grade, route information and crag information.
        Now also incorporates user-provided inputs and free-form description if available.
        Features are derived from:
            - route_angles → is_steep / is_technical
            - route_lengths → is_endurance / is_power
            - hold_types → is_crimpy / is_slopey / is_pockety
            - route_description → keyword‐map lookup (DESCRIPTION_KEYWORDS)
        Returns a dict of:
            - boolean flags (is_steep, is_power, is_technical, is_crimpy, is_slopey, is_endurance, is_pockety, …)  
            - primary_style  
            - key_challenges (list of strings)  
            - grade (raw string)
        """
        features = {
            "is_steep": False,
            "is_technical": False,
            "is_endurance": False,
            "is_power": False,
            "is_crimpy": False,
            "is_slopey": False,
            "is_pockety": False,
            "is_pumpy": False,
            "is_sustained": False,
            "is_bouldery": False,
            "is_dynamic": False,
            "primary_style": "mixed",
            "key_challenges": [],
            "route_style": None  # Store the actual style selection
        }
        
        # 3) Preserve the raw grade string for downstream use
        features["grade"] = grade
        
        # Now incorporate user-provided route characteristics if available
        if user_data:
            # Route Style
            if user_data.route_style:
                style = user_data.route_style.lower()
                features["route_style"] = user_data.route_style

                if "bouldery" in style:
                    features["is_bouldery"] = True
                    features["is_power"] = True
                    features["key_challenges"].append("bouldery sequences")
                
                elif "pumpy" in style:
                    features["is_pumpy"] = True
                    features["is_endurance"] = True
                    features["key_challenges"].append("pump management")
                    
                elif "sustained" in style:
                    features["is_sustained"] = True
                    features["is_endurance"] = True
                    features["key_challenges"].append("sustained effort")
                    
                elif "endurance" in style and "focused" in style:
                    features["is_endurance"] = True
                    features["key_challenges"].append("endurance")
                    
                elif "power" in style and "endurance" in style:
                    features["is_pumpy"] = True  # Power-endurance is pumpy
                    features["is_endurance"] = True
                    features["is_power"] = True
                    features["key_challenges"].append("power-endurance")
                    
                elif "technical" in style:
                    features["is_technical"] = True
                    features["key_challenges"].append("technical movement")
                    
                elif "dyno" in style or "dynamic" in style:
                    features["is_dynamic"] = True
                    features["is_power"] = True
                    features["key_challenges"].append("dynamic movement")
                    
                elif "fingery" in style:
                    features["is_crimpy"] = True
                    features["key_challenges"].append("finger strength")
            
            # Route angles
            if user_data.route_angles:
                angles = [angle.strip().lower() for angle in user_data.route_angles.split(",")]
                if "overhanging" in angles or "roof" in angles:
                    features["is_steep"] = True
                    if "steepness" not in features["key_challenges"]:
                        features["key_challenges"].append("steepness")
                if "slab" in angles:
                    features["is_technical"] = True
                    if "technical movement" not in features["key_challenges"]:
                        features["key_challenges"].append("technical movement")
            
            # Route lengths
            if user_data.route_lengths:
                lengths = [length.strip().lower() for length in user_data.route_lengths.split(",")]
                if "long" in lengths:
                    features["is_endurance"] = True
                    if "endurance" not in features["key_challenges"]:
                        features["key_challenges"].append("endurance")
                if "short" in lengths or "bouldery" in lengths:
                    features["is_power"] = True
                    if "power" not in features["key_challenges"]:
                        features["key_challenges"].append("power")
            
            # Hold types
            if user_data.hold_types:
                hold_types = [hold.strip().lower() for hold in user_data.hold_types.split(",")]
                if "crimpy" in hold_types or "crack" in hold_types:
                    features["is_crimpy"] = True
                    if "small holds" not in features["key_challenges"]:
                        features["key_challenges"].append("small holds")
                if "slopers" in hold_types:
                    features["is_slopey"] = True
                    if "slopers" not in features["key_challenges"]:
                        features["key_challenges"].append("slopers")
                if "pockets" in hold_types:
                    features["is_pockety"] = True
                    if "pockets" not in features["key_challenges"]:
                        features["key_challenges"].append("pockets")
                if "pinches" in hold_types:
                    if "pinches" not in features["key_challenges"]:
                        features["key_challenges"].append("pinches")
            
            # Route description (free-form) - feature flahs via keyword map
            if user_data and user_data.route_description:
                desc = user_data.route_description.lower()
                for flag, cfg in DESCRIPTION_KEYWORDS.items():
                    # if any keyword appears in the description, set the flag & record the challenge
                    if any(kw in desc for kw in cfg["keywords"]):
                        features[flag] = True
                        if cfg["challenge"] not in features["key_challenges"]:
                            features["key_challenges"].append(cfg["challenge"])
        
        # Set primary style based on detected features
        if features.get("route_style"):
            # Use the explicitly selected style as primary
            features["primary_style"] = features["route_style"].lower()
        elif features["is_steep"] and features["is_power"]:
            features["primary_style"] = "powerful overhanging"
        elif features["is_steep"] and features["is_endurance"]:
            features["primary_style"] = "endurance overhanging"
        elif features["is_technical"] and not features["is_steep"]:
            features["primary_style"] = "technical face"
        elif features["is_endurance"] and not features["is_steep"]:
            features["primary_style"] = "sustained vertical"
        elif features["is_crimpy"] and features["is_technical"]:
            features["primary_style"] = "technical crimping"
        elif features["is_pockety"]:
            features["primary_style"] = "pocket-intensive"
        elif features["is_pumpy"]:
            features["primary_style"] = "pumpy"
        elif features["is_bouldery"]:
            features["primary_style"] = "bouldery"
    
        
        # Remove duplicate key challenges
        features["key_challenges"] = list(dict.fromkeys(features["key_challenges"]))
        
        return features
    
    
    def generate_preview(self, data: PhasePlanRequest) -> dict:
        """Generate a lightweight preview with route analysis and training approach."""
        
        # Analyze the route to get features
        route_features = self.analyze_route(data.route, data.grade, data.crag, user_data=data)
        
        preview_prompt = f"""
        You are an expert climbing coach. Analyze this route and climber profile:
        
        Route: {data.route}, Grade: {data.grade}, Location: {data.crag}
        
        Route Details:
        - Primary style: {route_features['primary_style']}
        - Key challenges: {', '.join(route_features['key_challenges']) if route_features['key_challenges'] else 'varied'}
        - Steepness: {"steep or overhanging" if route_features['is_steep'] else "vertical or less"}
        - Hold types: {"crimpy" if route_features['is_crimpy'] else ""}{"slopey" if route_features['is_slopey'] else ""}{"pockety" if route_features['is_pockety'] else ""}{"varied" if not (route_features['is_crimpy'] or route_features['is_slopey'] or route_features['is_pockety']) else ""}
        
        User-provided route characteristics:
        - Angles: {data.route_angles}
        - Lengths: {data.route_lengths}
        - Hold types: {data.hold_types}
        - Style: {data.route_style}
        - Additional description: {data.route_description}
        
        Climber Profile:
        - Current sport grade: {data.current_climbing_grade}
        - Max boulder grade: {data.max_boulder_grade}
        - Strengths: {data.perceived_strengths}
        - Weaknesses: {data.perceived_weaknesses}
        - Facilities available: {data.training_facilities}
        - Injury history: {data.injury_history}
        
        Provide TWO concise paragraphs:
        1. Route Overview: Give an overview of the route.
           Analyze the style and demands of this route based on the details provided.
           Include references to specific features the user identified (angles, holds, length) if relevant.
           
        2. Training Approach: 
           Outline what areas a training plan should focus on for this route given the climber's profile.
           Address the user's specific needs based on the route characteristics they identified.
           IMPORTANT: Address the user directly using "you" and "your" instead of "the climber"
           (e.g., "Given your profile" instead of "Given the climber's profile")
        
        Return only a JSON object with 'route_overview' and 'training_approach' fields.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert climbing coach. Return only valid JSON."
                    },
                    {"role": "user", "content": preview_prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            # Process the response
            raw_json = response.choices[0].message.content.strip()
            
            # Clean up any potential markdown formatting
            if raw_json.startswith("```"):
                raw_json = raw_json.strip("```json\n")
            if raw_json.endswith("```"):
                raw_json = raw_json.rstrip("```")
            raw_json = raw_json.strip()
            
            # Parse the JSON
            parsed = json.loads(raw_json)
            
            return {
                "route_overview": parsed.get("route_overview", ""),
                "training_approach": parsed.get("training_approach", "")
            }
        
        except Exception as e:
            logger.error(f"Error generating plan preview: {str(e)}")
            raise
    
    def get_valid_exercise_names(self) -> List[str]:
        """Returns a list of all valid exercise names from the database."""
        all_exercises = db.get_exercises()
        return [ex["name"] for ex in all_exercises]
    
    def validate_and_fix_exercise_names(self, plan_data: dict, valid_names: List[str]) -> dict:
        """Validate exercise names and attempt to fix invalid ones."""
        from difflib import get_close_matches
        
        fixed_plan = plan_data.copy()
        errors = []
        fixes = []
        
        for phase_idx, phase in enumerate(fixed_plan.get("phases", [])):
            for day_idx, day in enumerate(phase.get("weekly_schedule", [])):
                focus = day.get("focus", "")
                
                # Split by '+' for combined exercises
                focus_parts = [part.strip() for part in focus.split("+")]
                fixed_parts = []
                
                for part in focus_parts:
                    if part in valid_names:
                        fixed_parts.append(part)
                    else:
                        # Try fuzzy matching
                        matches = get_close_matches(part, valid_names, n=1, cutoff=0.8)
                        if matches:
                            fixed_parts.append(matches[0])
                            fixes.append(f"Fixed '{part}' -> '{matches[0]}'")
                            logger.warning(f"Auto-fixed exercise name: '{part}' -> '{matches[0]}'")
                        else:
                            errors.append(f"Invalid exercise: '{part}' in phase {phase_idx+1}, day {day_idx+1}")
                
                # Update the focus with fixed names
                if fixed_parts:
                    fixed_plan["phases"][phase_idx]["weekly_schedule"][day_idx]["focus"] = " + ".join(fixed_parts)
        
        if errors:
            raise ValueError(f"Invalid exercises found: {'; '.join(errors)}")
        
        if fixes:
            logger.info(f"Applied fixes: {'; '.join(fixes)}")
        
        return fixed_plan
    
    def extract_exercise_details(self, exercise_name: str, full_details: str) -> str:
        """
        Attempt to extract details specific to a particular exercise from the full workout details.
        Returns empty string if no specific details found.
        """
        exercise_lower = exercise_name.lower()
        full_details_lower = full_details.lower()
        
        # Look for exact exercise name in details
        if exercise_lower in full_details_lower:
            # Try to find the start of this exercise's details
            start_idx = full_details_lower.find(exercise_lower)
            if start_idx >= 0:
                # Found the exercise name, now get all text after it
                start_idx = start_idx + len(exercise_lower)
                
                # Try to find the next exercise name (if any)
                next_idx = len(full_details)
                for common_term in ["fingerboard", "campus", "boulder", "core", "anaerobic", "repeater", "hang", "density"]:
                    if common_term != exercise_lower and common_term in full_details_lower[start_idx:]:
                        term_idx = full_details_lower[start_idx:].find(common_term) + start_idx
                        next_idx = min(next_idx, term_idx)
                
                # Extract just the relevant portion
                if next_idx > start_idx:
                    return full_details[start_idx:next_idx].strip()
        
        # Fallback: look for exercise-specific keywords
        if "fingerboard" in exercise_lower:
            keywords = ["hang", "edge", "seconds", "rest", "crimp", "repeater"]
            for keyword in keywords:
                if keyword in full_details_lower:
                    # Find paragraph containing this keyword
                    paragraphs = full_details.split("\n")
                    for para in paragraphs:
                        if keyword in para.lower():
                            return para.strip()
        
        elif "core" in exercise_lower:
            keywords = ["lever", "plank", "leg raise", "ab", "core"]
            for keyword in keywords:
                if keyword in full_details_lower:
                    # Find paragraph containing this keyword
                    paragraphs = full_details.split("\n")
                    for para in paragraphs:
                        if keyword in para.lower():
                            return para.strip()
        
        elif "boulder" in exercise_lower:
            keywords = ["problem", "boulder", "v-grade", "limit"]
            for keyword in keywords:
                if keyword in full_details_lower:
                    # Find paragraph containing this keyword
                    paragraphs = full_details.split("\n")
                    for para in paragraphs:
                        if keyword in para.lower():
                            return para.strip()
        
        # No specific details found
        return ""
    
    def validate_training_plan(self, plan_data: dict) -> Tuple[bool, str]:
        """
        Validates a generated training plan against methodology rules.
        Returns (is_valid, error_message).
        """
        try:
            # Check for required top-level fields
            required_fields = ["route_overview", "training_overview", "phases"]
            for field in required_fields:
                if field not in plan_data:
                    return False, f"Missing required field: {field}"
            
            phases = plan_data.get("phases", [])
            if not phases or not isinstance(phases, list):
                return False, "Plan must contain at least one phase"
            
            # Validate each phase
            for i, phase in enumerate(phases):
                # Check phase structure
                if not isinstance(phase, dict):
                    return False, f"Phase {i} is not a valid object"
                
                phase_fields = ["phase_name", "description", "weekly_schedule"]
                for field in phase_fields:
                    if field not in phase:
                        return False, f"Phase {i} missing field: {field}"
                
                # Check weekly schedule
                schedule = phase.get("weekly_schedule", [])
                if not schedule or not isinstance(schedule, list):
                    return False, f"Phase {i} must have a weekly schedule with at least one day"
                
                # Validate each day in the schedule
                for j, day in enumerate(schedule):
                    if not isinstance(day, dict):
                        return False, f"Day {j} in phase {i} is not a valid object"
                    
                    day_fields = ["day", "focus", "details"]
                    for field in day_fields:
                        if field not in day:
                            return False, f"Day {j} in phase {i} missing field: {field}"
                    
                    # Validate day is a valid day of the week
                    valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                                 "Friday", "Saturday", "Sunday"]
                    if day.get("day") not in valid_days:
                        return False, f"Invalid day in phase {i}, day {j}: {day.get('day')}"
                    
                    # Check if details has minimum content
                    details = day.get("details", "")
                    if len(details) < 50:  # Arbitrary minimum length for meaningful details
                        return False, f"Details too short in phase {i}, day {j}"
            
            return True, "Plan is valid"
        
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def create_phase_based_prompt(self, data: PhasePlanRequest, weeks: int, sessions: int, previous_analysis: str = None) -> str:
        """
        Returns a prompt instructing the model to produce a PHASE-based plan.
        """
        # First, analyze the route using the enhanced function with user data
        route_features = self.analyze_route(data.route, data.grade, data.crag, user_data=data)

        available_facilities = self.exercise_filter.parse_available_facilities(data.training_facilities)
        facilities_text = ", ".join(available_facilities)

        session_time_str = data.time_per_session
        session_time_minutes = 120 # Default to 2 hours
        
        # Extract numeric time value
        time_match = re.search(r'(\d+(?:\.\d+)?)', session_time_str)
        if time_match:
            time_value = float(time_match.group(1))
            if "hour" in session_time_str.lower():
                session_time_minutes = int(time_value * 60)
            elif "minute" in session_time_str.lower() or "min" in session_time_str.lower():
                session_time_minutes = int(time_value)
            else:
                session_time_minutes = int(time_value * 60)
        
        # Get all exercises from DB
        all_exercises = db.get_exercises()
        
        # Filter and rank them based on route features and climber profile
        ranked_exercises = self.exercise_filter.filter_exercises_enhanced(all_exercises, data, route_features)
        
        # Create minimal exercise data to save tokens
        minimal_exercises = []
        for ex in ranked_exercises:
            # Only include essential information plus time requirement
            minimal_ex = {
                "name": ex["name"],
                "type": ex["type"],
                "priority": ex.get("priority", "medium"),
                "time_required": ex.get("time_required", 30)
            }
            
            # Include compatible exercises if available
            if "compatible_with" in ex:
                minimal_ex["compatible_with"] = ex["compatible_with"]
                
            minimal_exercises.append(minimal_ex)

        # Convert to JSON
        exercises_json = json.dumps(minimal_exercises, indent=2)
        
        # Parse attribute ratings for more nuanced prompt generation
        attribute_ratings = self.exercise_filter.parse_attribute_ratings(data.attribute_ratings)
        strengths = []
        weaknesses = []
        neutral = []

        # Handle attribute ratings if available
        if attribute_ratings:
            # Consider ratings 4-5 as strengths, 1-2 as weaknesses, 3 as neutral
            for attr, rating in attribute_ratings.items():
                if rating >= 4:
                    strengths.append(f"{attr} ({rating}/5)")
                elif rating <= 2:
                    weaknesses.append(f"{attr} ({rating}/5)")
                else:
                    neutral.append(attr)
        else:
            # Fall back to legacy strengths/weaknesses fields if no ratings
            strengths = data.perceived_strengths.split(", ") if data.perceived_strengths else []
            weaknesses = data.perceived_weaknesses.split(", ") if data.perceived_weaknesses else []
        
        strengths_text = ", ".join(strengths) if strengths else "None specified"
        weaknesses_text = ", ".join(weaknesses) if weaknesses else "None specified"
        
        # Add previous analysis if provided
        previous_analysis_text = ""
        if previous_analysis:
            previous_analysis_text = f"""
Based on this previous analysis of the route and climber:
{previous_analysis}

Now generate a detailed phase-based training plan that aligns with this assessment.
"""

        # Format the user-provided route characteristics in a readable way
        route_characteristics = f"""
The climber provided these specific details about the route:
- Route angles: {data.route_angles if data.route_angles else "Not specified"}
- Route length: {data.route_lengths if data.route_lengths else "Not specified"}
- Hold types: {data.hold_types if data.hold_types else "Not specified"}
- Additional description: {data.route_description if data.route_description else "Not provided"}

Based on this information and analysis of the route name, the route has these features:
- Primary style: {route_features['primary_style']}
- Key challenges: {', '.join(route_features['key_challenges'])}
- Technical: {'Yes' if route_features['is_technical'] else 'No'}
- Steep/Overhanging: {'Yes' if route_features['is_steep'] else 'No'}
- Endurance-focused: {'Yes' if route_features['is_endurance'] else 'No'}
- Power-focused: {'Yes' if route_features['is_power'] else 'No'}
- Small holds/crimpy: {'Yes' if route_features['is_crimpy'] else 'No'}
- Slopers: {'Yes' if route_features['is_slopey'] else 'No'}
- Pockets: {'Yes' if route_features['is_pockety'] else 'No'}
"""

        # Get valid exercise names for validation
        valid_exercise_names = self.get_valid_exercise_names()
        exercise_names_list = "\n".join([f"- \"{name}\"" for name in valid_exercise_names])
        
        # Add explicit instruction to use only valid exercise names
        exercise_instruction = f"""
CRITICAL INSTRUCTION: You MUST ONLY use the exact exercise names from this list in the 'focus' field of your output:
{exercise_names_list}

DO NOT use generic names like "Finger Strength" or "Power" in the 'focus' field. 
Instead, use the specific exercise names from the list above.
You can combine exercises with "+" if needed, like "Fingerboard Max Hangs + Boulder 4x4s".

If you use any exercise name not in this list, your response will be rejected.
"""

        # Return the final prompt with enhanced route information
        return f"""
{previous_analysis_text}
You are an expert climbing coach. The climber has these details:
- Target route: {data.route}, grade {data.grade} at {data.crag}
- They have {weeks} weeks total to train, with {sessions} sessions per week.
- Current climbing grade: {data.current_climbing_grade}
- Max boulder grade: {data.max_boulder_grade}
- Training experience: {data.training_experience}
- Strengths: {strengths_text}
- Weaknesses: {weaknesses_text}
- Session time: {data.time_per_session}
- Facilities: {data.training_facilities}
- Injuries: {data.injury_history}
- Other notes: {data.additional_notes}

{route_characteristics}

We want to break the training down into PHASES (e.g. Strength/Power, Power-Endurance, etc.),
each phase spanning certain weeks. For each phase:
1. Give a 'phase_name' (e.g. "Strength & Power (Weeks 1-4)").
2. Provide a high-level 'description' of the goals for that phase.
3. Show a 'weekly_schedule' array with day-by-day breakdown:
   - For each day, specify the focus and a 'details' field describing the workout thoroughly.
   - If you use an exercise from the library, expand it with sets, reps, rest intervals, etc.

Return valid JSON in the format:

{{
    "instruction": "Create a structured climbing training plan according to these specifications",
    "required_format": {{
        "route_overview": "string describing route demands",
        "training_overview": "string summarizing training approach",
        "phases": [
            {{
                "phase_name": "string",
                "description": "string about goals of the phase",
                "weekly_schedule": [
                    {{
                        "day": "Monday",
                        "focus": "e.g. Campus & Hard Bouldering",
                        "details": "Detailed instructions on sets, reps, rests..."
                    }},
                    ...
                ]
            }},
            ...
        ]
    }}

Below is a reference training library you can draw from. 
**IMPORTANT**: You MUST ONLY use exercises from the provided exercise library. Do not invent or suggest exercises not in this list. The exact exercise names must match those provided.

These exercises have already been filtered based on:
1. The climber's available facilities ({facilities_text})
2. The session length ({session_time_minutes} minutes per session)

Each exercise includes a 'time_required' field that indicates how many minutes it typically takes. When planning sessions, make sure the total time of exercises doesn't exceed the climber's available time per session.

    training_library = {exercises_json},

    "energy_systems_glossery": {{
        "strength": "Maximum force production capability, developed through bouldering, fingerboarding and campus training...",
        "anaerobic_capacity (An Cap)": "Ability to sustain hard climbing (10-15 move sequences) ...",
        "aerobic_capacity (Aero Cap)": "Ability to climb without getting pumped ...",
        "anaerobic_power (An Pow)": "The power end of power-endurance ...",
        "aerobic_power (Aero Pow)": "The endurance end of power-endurance ..."
    }},

    "training_rules": [
        {{
            "type": "time_management",
            "rules": [
                "Each exercise includes a 'time_required' value (in minutes) that must be considered when planning sessions",
                "The total time of exercises in a session should NOT exceed the climber's available time ({session_time_minutes} minutes)",
                "Include warm-up (10-15 min) and cool-down (5-10 min) in the time calculation",
                "For longer sessions, prioritize variety with 2-3 complementary exercises rather than a single long exercise",
                "Short sessions (under 60 minutes) should focus on 1-2 exercises plus warm-up/cool-down",
                "Medium sessions (60-90 minutes) can include 2-3 exercises plus warm-up/cool-down",
                "Long sessions (90+ minutes) can include 3-4 exercises plus warm-up/cool-down",
                "Remember to account for transition time between exercises (typically 3-5 minutes)"
            ]
        }},
        {{
            "type": "phase_structure",
            "rules": [
                "Start with strength & power phase unless explicitly strong in these areas",
                "However, reduce or omit strength phase if route is purely endurance-focused",
                "Phase length depends on total weeks: 6w=2w, 7w=2-3w, 8w=3w, 9w+=3-4w",
                "Keep strong focus on strength/power for short/bouldery routes"
            ]
        }},
        {{
            "type": "training_periodization",
            "rules": [
                "These are guidelines that should be adapted based on the climber's strengths, weaknesses and particularly the specific route demands",
                "Typical structure: Base Phase (early) and Peak Phase (later), with proper tapering at the end",
                "Base Phase: Generally focuses on strength, An Cap and Aero Cap, but prioritize differently based on individual needs",
                "Peak Phase: Typically shifts toward An Pow and Aero Pow while maintaining strength, but adjust based on route requirements",
                "For strength-dependent routes: Maintain higher strength focus throughout or if the climber is weak in this area",
                "For endurance-dependent routes: Reduce strength work if the climber is already strong in this area",
                "Adjust phase timing (general guidelines - not rules): 6-week plans ~4w/2w, 8-week plans ~4w/4w, 10-12 week plans ~5-7w/5-7w",
                "In Base Phase: An Cap work typically 1-2 sessions/week depending on needs and recovery ability but mostly focuses on strength/power",
                "In Base Phase: Aero Cap work scales up in second half for most climbers, unless route is short or bouldery",
                "In Peak Phase: An Pow and Aero Pow emphasis should match route characteristics - not automatically 2 sessions each",
                "Route-specific adjustments trump general guidelines - analyze the route demands carefully",
                "For bouldery/powerful routes: Maintain higher strength/power focus even in later phases",
                "Include tapering period (typically 1 week) with reduced volume (around 50%) before the end of the plan",
                "During taper: Typically drop An Cap, Aero Cap and ARC work while focusing on quality over quantity",
                "Consider maintaining some An Cap work (usually 1x/week or added to another session) until 4 weeks before the goal, unless already strong",
                "Always progress from general to specific training as weeks advance",
                "Consider a deload week with reduced volume mid-plan for longer training cycles (>13 weeks)"
            ]
        }},
        {{
            "type": "session_intensity",
            "rules": [
                "When combining exercises in a session, start with highest intensity and work down",
                "Proper order: strength/power → bouldering → An Cap/An Pow → Aero Pow → Aero Cap → ARC",
                "Hard anaerobic capacity work combines well with end of strength sessions",
                "Place anaerobic power work after bouldering but before aerobic work",
                "3 days/week maximum for 'hard' energy system work (An Cap, An Pow, Aero Pow)",
                "Technical, coordination-heavy exercises should be done when fresh",
                "Fingerboard and basic strength work can be done after technique work",
                "Basic conditioning and ARC can easily be added to end of sessions"    
            ]
        }},
        {{
            "type": "session_placement",
            "rules": [
                "Place high-intensity sessions early in week when energy is highest",
                "CRITICAL RULE: Separate campus and fingerboard sessions with AT LEAST ONE REST DAY",
                "CRITICAL RULE: Sunday and Monday are consecutive days in a training cycle - never schedule high-intensity sessions on both",
                "Never combine max hangs and campus board in same day",
                "Place technique work after full rest days for best learning",
                "Structure harder sessions with adequate rest between them",
                "Intensity hierarchy: campus sessions → max hangs → max boulders → repeaters → technique",
                "For 4-day training weeks, a sample structure might be: Mon (Strength), Wed (Power-Endurance), Fri (Strength), Sun (Endurance)"
            ]
        }},
        {{
            "type": "session_structure",
            "rules": [
                "Sessions should utilize most of the allocated time (typically 1.5-2 hours) by including appropriate volume",
                "A complete session typically includes: warm-up (10-15 min), main focus work (30-60 min), secondary/complementary work (20-30 min), and cool-down (5-10 min)",
                "Even when focusing on one energy system, complementary work targeting weaknesses should be included when time allows",
                "Technique work should rarely be the sole focus of a session unless specifically requested - instead include it within strength or endurance sessions",
                "Separate high-intensity exercises (campus, max hangs, limit bouldering) with at least 48 hours recovery for the same muscle groups",
                "NEVER schedule campus training the day before or after max hangs or intensive pull-based strength training",
                "For weekly scheduling, consider the entire week as a cycle - avoid having the last session of one week and first session of next week both be high intensity",
                "For climbers below V5/6B+, campus training should NOT be included regardless of ability level",
                "When a climber has identified weaknesses (endurance, power endurance, etc.), include work targeting these weaknesses from the beginning of the plan",
                "Provide realistic volume for all sessions: bouldering (1-2 hours), fingerboard (20-30 minutes), endurance circuits (45-90 minutes)",
                "Avoid excessively short sessions - a standard training session should never be less than 45 minutes total",
                "A single type of exercise (e.g., 'Technique Drills') is never sufficient for a full session - combine with other exercises"
            ]
        }},
        {{
            "type": "training_plan_structure",
            "rules": [
                "When a climber has specific weaknesses, these must be addressed from phase 1 - don't delay training all weaknesses until later phases",
                "For climbers with endurance weaknesses: include at least 1 endurance-focused session even in the strength phase",
                "For climbers with strength weaknesses: maintain strength work (at reduced volume) even in endurance phases",
                "'Maintaining' an energy system means including at least 1 session per week targeting that system",
                "In early phases, higher priority weaknesses get 2 sessions per week while maintaining strengths gets 1 session",
                "A 4-session week typically includes: 2 sessions of phase priority, 1 session targeting weakness, 1 session of supporting work",
                "For pure sport route climbers, never have a week with only strength/power work or only endurance work",
                "For boulderers, it's acceptable to have strength-only phases, but still include some power-endurance",
                "Follow a logical progression for each energy system (e.g., ARC → 4x4s → Route Intervals)",
                "Distribute hard sessions throughout the week with proper recovery days between",
                "High/low/medium/off scheduling is often more effective than constant intensity",
                "For a 10-week plan, consider including a deload week around week 5-6 with 50% reduced volume",
                "The final week of any plan should include a taper (reduced volume, maintained intensity) to prepare for the goal"
            ]
        }},
        {{
            "type": "progression",
            "rules": [
                "Increase difficulty through volume or intensity each week",
                "Progress from general to specific training as weeks advance",
                "Adjust volume based on climber's recovery capacity and experience"
            ]
        }},
        {{
            "type": "exercise_selection",
            "rules": [
                "Choose exercises matching route characteristics",
                "Include 1-2 core training sessions per week",
                "Balance skill development with physical training",
                "Focus on climber's weaknesses while maintaining strengths"
            ]
        }},
        {{
            "type": "safety_adjustments",
            "rules": [
                "Omit campus boarding for climbers with less than 1 year experience",
                "Reduce fingerboard intensity for beginners",
                "Modify exercises based on injury history",
                "Include proper warm-up and cool-down for each session"
            ]
        }},
        {{
            "type": "campus_board_training",
            "rules": [
                "Only include campus board for climbers at V5/6B+ or higher (about 7b or higher)",
                "Beginners (<1 year experience) should NEVER campus regardless of grade",
                "Only include campus board in Strength & Power Phase (4-8 weeks before project)",
                "Limit to 1-2 sessions per week with 48+ hours rest between",
                "Sessions must be high-intensity with 2-5 minutes rest between attempts",
                "Always warm up with dynamic bouldering before campus training",
                "Progression: ladders → touches → max moves → doubles → plyometrics",
                "Intermediate climbers (V5-V7): Focus on ladders, touches, and basic max moves",
                "Advanced climbers (V7+/5.13a+): Include doubles, skip ladders, and plyometrics",
                "'Foot-on campussing' is NOT included as 'campus_board_training'"
            ]
        }},
        {{
            "type": "fingerboard_training",
            "rules": [
                "Beginners (<1 year): Avoid fingerboard unless already doing structured training",
                "Intermediate (1-3 years, V4+): Limit to 1-2 sessions/week with 48+ hours recovery",
                "Advanced (3+ years, V6+): Use 2-3 times/week as part of structured plan", 
                "Use Max Hangs for strength development (10-12 second hangs, 3-5 min rest, 3-5 sets)",
                "Use Repeaters for endurance (7s hang/3s rest x 6 reps, 3 min rest, 3-5 sets)",
                "Place fingerboard work after warm-up, before climbing or at start of strength sessions",
                "Never combine intense fingerboard with campus board on same day",
                "Reduce to 1 session/week during pre-performance phase (2-4 weeks before project)",
                "Choose appropriate grip type (half crimp, open hand, or full crimp) based on route",
                "Progress by reducing edge size, adding weight, or extending hang duration",
                "Balance with antagonist training (wrist extensors) for injury prevention",
                "If the route has many pockets, suggest fingerboard sessions with pockets"   
            ]
        }},
        {{
            "type": "technique_drills",
            "rules": [
                "Do not include technique drills if the climber grade is >6c or max boulder is >6B",
                "Technique drills should only be includes as part of the climbers warm up",
                "Technique drills should be addressed where it is a weakness"
            ]
        }},
    
        {{
            "type": "example_workouts",
            "examples": [
                {{
                    "focus": "Strength & Bouldering Session",
                    "format": "1) Warm-up: 15 min general climbing, progressive difficulty \\n2) Main focus: 60-90 min of limit bouldering or max hangs \\n3) Complementary: 20-30 min core work or antagonist training \\n4) Cool-down: 5-10 min easy climbing or stretching"
                }},
                {{
                    "focus": "Endurance Session",
                    "format": "1) Warm-up: 15 min progressive climbing \\n2) Main focus: 45-60 min of ARC, 4x4s, or circuit training \\n3) Complementary: 20 min technique drills or light strength maintenance \\n4) Cool-down: 5-10 min easy climbing"
                }},
                {{
                    "focus": "Power-Endurance Session",
                    "format": "1) Warm-up: 15-20 min progressive climbing \\n2) Main focus: 40-60 min of linked boulders, intervals, or circuits \\n3) Complementary: 20 min technique or light strength \\n4) Cool-down: 5-10 min easy climbing"
                }},
                {{
                    "focus": "Technique Session (combined with climbing)",
                    "format": "1) Warm-up: 15 min general climbing \\n2) Technique drills: 30 min focused drills \\n3) Practical application: 45-60 min of climbing applying the techniques \\n4) Cool-down: 5-10 min easy climbing or stretching"
                }}
            ]
        }}
    ]
}},

    "Your task: 
        - Split the total {weeks} weeks into appropriate phases for the climber's route style.
        - For each day (Mon, Tue, etc.) in each phase, specify the focus/workout.
        - For fingerboard or campus, specify recommended edge size or time under tension, rest intervals, # sets, etc.
        - Keep the final output strictly valid JSON with no extra commentary. 
        - Use the structure {{\"phases\": [...]}} exactly.
        
{exercise_instruction}

Return only JSON with a top‐level structure containing route_overview, training_overview, and phases array. No extra text, no markdown:
"""

    def generate_full_plan(
        self,
        request: FullPlanRequest,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> dict:
        """Generate a full training plan using deterministic phases."""
        
        # Extract data from request
        plan_data = request.plan_data
        previous_analysis = request.previous_analysis
        weeks = int(plan_data.weeks_to_train)
        sessions = int(plan_data.sessions_per_week)

        # Step 1: Analyze route
        route_features = self.analyze_route(
            plan_data.route, 
            plan_data.grade, 
            plan_data.crag, 
            user_data=plan_data
        )
        
        # Step 2: Get attribute ratings
        attribute_ratings = self.exercise_filter.parse_attribute_ratings(
            plan_data.attribute_ratings
        )
        
        # Step 3: Determine phases algorithmically
        phases, training_days = self.phase_structure.determine_phase_structure(
            plan_data,
            weeks,
            sessions,
            route_features,
            attribute_ratings
        )
        
        logger.info(f"Determined {len(phases)} phases for {weeks}-week plan")
        logger.info(f"Training days: {training_days}")
        
        # Step 4: Generate the complete plan
        complete_plan = {
            "phases": []
        }
        
        # Get all exercises once
        all_exercises = db.get_exercises()
        valid_exercise_names = self.get_valid_exercise_names()
        
        # For each phase, filter exercises and generate schedule
        for idx, phase in enumerate(phases):
            logger.info(f"Generating phase {idx+1}/{len(phases)}: {phase['name']}")
            
            # Filter exercises for this specific phase
            phase_exercises = self.exercise_filter.filter_exercises_enhanced(
                all_exercises,
                plan_data,
                route_features,
                phase_type=phase['type'],
                phase_weeks=phase['weeks']
            )
            
            # Try up to 3 times for each phase
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Create phase-specific prompt
                    phase_prompt = self._create_phase_specific_prompt(
                        plan_data,
                        phase,
                        phase_exercises,
                        sessions,
                        training_days,
                        previous_analysis
                    )
                    
                    if attempt > 0:
                        phase_prompt += f"\n\nIMPORTANT: Previous attempt failed. You MUST use ONLY these exact exercise names:\n{chr(10).join([ex['name'] for ex in phase_exercises[:20]])}"
                    
                    # Generate schedule for this phase
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are an expert climbing coach. Return only valid JSON."},
                            {"role": "user", "content": phase_prompt}
                        ],
                        temperature=0.2 if attempt == 0 else 0.1,
                        max_tokens=4000,
                        request_timeout=60
                    )
                    
                    raw_json = response.choices[0].message.content.strip()
                    if raw_json.startswith("```"):
                        raw_json = raw_json.strip("```json\n").rstrip("```")
                    
                    phase_schedule = json.loads(raw_json)
                    
                    # Validate and fix exercise names for this phase
                    fixed_schedule = self._validate_phase_exercises(
                        phase_schedule, 
                        [ex['name'] for ex in phase_exercises]
                    )
                    
                    # Post-process to separate exercises if needed
                    if "weekly_schedule" in fixed_schedule:
                        for day in fixed_schedule["weekly_schedule"]:
                            if "+" in day.get("focus", ""):
                                focus_parts = [part.strip() for part in day["focus"].split("+")]
                                day["exercises"] = []
                                original_details = day["details"]
                                
                                for focus_part in focus_parts:
                                    exercise_detail = self.extract_exercise_details(focus_part, original_details)
                                    day["exercises"].append({
                                        "name": focus_part,
                                        "details": exercise_detail or original_details
                                    })
                    # —— Enforce high‐intensity exercises first in each session —— #
                    DAY_INTENSITY_ORDER = {
                        # === Highest-intensity “strength/power” ===
                        "Campus Board Exercises":               0,
                        "Campus Board Exercises (Power)":       0,
                        "Campus Board Exercises (Strength)":    0,
                        "Explosive Pull-Ups":                   0,
                        "Fingerboard Max Hangs":                0,
                        "Fingerboard Max Hangs (Crimps)":       0,  
                        "Fingerboard Max Hangs (Pockets)":      0,      
                        "Fingerboard Max Hangs (Slopers)":      0,    
                        "Fingerboard Max Hangs (Drag)":         0, 
                        "Campus Bouldering":                    1,   
                        "Max Boulder Sessions":                 2,
                        "Board Session":                        2,
                        "Boulder Pyramids":                     2,
                        "Weighted Pull-Ups":                    4,
                        "One-Arm Lock-Offs":                    4,
                        "Boulder Intervals":                    5,

                        # === Anaerobic-capacity ===
                        "Long Boulder Circuits":                6,
                        "Boulder Triples":                      6,
                        "Linked Bouldering Circuits":           6,
                        "Campus Laddering":                     6,
                        "Fingerboard Repeater Blocks":          6,
                        "Multiple Set Boulder Circuits":        6,
                        "Density Hangs":                        6,
 
                        # === Anaerobic-power ===
                        "Short Boulder Repeats":                6,
                        "Broken Circuits":                      6,
                        "Max Intensity Redpoints":              6,

                        # === Aerobic-power ===
                        "Boulder 4x4s":                         8,
                        "3x3 Bouldering Circuits":              8,  
                        "Intensive Foot-On Campus":             8,
                        "30-Move Circuits":                     8,
                        "On-The-Minute Bouldering":             8,

                        # === Aerobic-power ===
                        "Volume Bouldering":                    10,
                        "Free Bouldering":                      11,

                        # === Aerobic-capacity / ARC ===
                        "Continuous Low-Intensity Climbing":    12,
                        "Mixed Intensity Laps":                 12,
                        "X-On, X-Off Intervals":                12,
                        "Route 4x4s":                           12,
                        "Linked Laps":                          12,
                        "Low Intensity Fingerboarding":         12,
                        "Foot-On Campus Endurance":             12,

                        # === Core work ===
                        "Front Lever Progressions":             14,
                        "Hanging Knee Raises":                  16,
                        "Window Wipers":                        16,
                        "Plank":                                16,
                        "Hanging Leg Raises":                   16,

                        # === Technique / skill drills ===
                        "Silent Feet Drills":                   20,
                        "Flagging Practice":                    20,
                        "High-Step Drills":                     20,
                        "Slow Climbing":                        20,
                        "Dynamic Movement Practice":            20,
                        "Rest Position Training":               20,
                        "Open-Hand Grip Practice":              20,
                        "Cross-Through Drills":                 20,

                        # === Mobility ===
                        "Flexibility and Mobility Circuit":     24,
                        "Dynamic Hip Mobility":                 24,
                        "Shoulder Mobility Flow":               24,
                        "Ankle and Foot Mobility":              24,
                    }

                    def sort_focus(focus_str):
                        parts = [p.strip() for p in focus_str.split("+")]
                        parts.sort(key=lambda p: DAY_INTENSITY_ORDER.get(p, 99))
                        return " + ".join(parts)

                    for day in fixed_schedule["weekly_schedule"]:
                        day["focus"] = sort_focus(day["focus"])
                    # — end intensity sort — #
                    
                    # Add to complete plan
                    complete_plan["phases"].append({
                        "phase_name": phase['name'],
                        "description": phase['description'],
                        "weekly_schedule": fixed_schedule.get("weekly_schedule", [])
                    })     
            
                    if on_progress:
                        on_progress(idx + 1, len(phases))
                    
                    break  # Success, move to next phase
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Phase {idx+1} attempt {attempt+1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise ValueError(f"Failed to generate phase {idx+1} after {max_retries} attempts: {e}")
                    continue
                    
                except Exception as e:
                    logger.error(f"Error generating phase {idx+1}: {e}")
                    raise
        
        # Ensure days are in correct order
        DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        for phase in complete_plan["phases"]:
            phase["weekly_schedule"].sort(
                key=lambda day: DAY_ORDER.index(day["day"])
            )

        return complete_plan

    def _create_phase_specific_prompt(
        self, 
        data: PhasePlanRequest,
        phase: Dict[str, Any],
        filtered_exercises: List[Dict[str, Any]],
        sessions_per_week: int,
        training_days: List[str],
        previous_analysis: Optional[str] = None
    ) -> str:
        """Create a prompt for generating a single phase's weekly schedule."""
        
        # Convert exercises to minimal JSON
        minimal_exercises = []
        for ex in filtered_exercises[:20]:  # Limit to top 20 to save tokens
            minimal_ex = {
                "name": ex["name"],
                "type": ex["type"],
                "time_required": ex.get("time_required", 30)
            }
            minimal_exercises.append(minimal_ex)
        
        exercises_json = json.dumps(minimal_exercises, indent=2)
        
        # Phase-specific guidance
        phase_guidance = {
            "base": """
    For this BASE phase, prioritize:
    - Strength development (fingerboard, max boulders)
    - Building work capacity (anaerobic capacity)
    - Addressing weaknesses identified in the climber profile
    - Maintaining aerobic base with at least one endurance session per week
    """,
            "peak": """
    For this PEAK phase, prioritize:
    - Power-endurance work (anaerobic power, aerobic power)
    - Route-specific training
    - Maintaining strength with reduced volume
    - Quality over quantity - higher intensity, lower volume
    """,
            "taper": """
    For this TAPER phase:
    - Reduce total volume by 40-50%
    - Maintain intensity on key exercises
    - Focus on feeling fresh and recovered
    - Include more technique and movement work
    - Avoid introducing new exercises or stimuli
    """
        }

        # Check if this phase has special emphasis (for endurance routes with endurance weakness)
        emphasis_guidance = ""
        if "emphasis" in phase and phase["emphasis"] == "aerobic_capacity":
            emphasis_guidance = """
    SPECIAL EMPHASIS FOR THIS PHASE:
    - This climber has WEAK ENDURANCE for an ENDURANCE ROUTE
    - Include AT LEAST 2-3 aerobic capacity sessions per week
    - Prioritize climbing-based endurance work (Continuous Low-Intensity Climbing, Route 4x4s, Mixed Intensity Laps)
    - Only use Low Intensity Fingerboarding as a supplement, not as primary endurance work
    - Strength work should be minimal - just maintenance
    """
        
        # Format training days
        days_str = ", ".join([f'"{day}"' for day in training_days])

        prompt = f"""
    You are generating the weekly schedule for a single phase of a climbing training plan.

    Phase: {phase['name']}
    Phase Type: {phase['type']} 
    Duration: {phase['weeks']} weeks
    Description: {phase['description']}

    Climber Profile:
    - Current grade: {data.current_climbing_grade}
    - Weaknesses: {data.perceived_weaknesses}
    - Available time: {data.time_per_session} per session
    - Sessions per week: {sessions_per_week}

    {phase_guidance.get(phase['type'], '')}

    Available exercises (already filtered for this phase):
    {exercises_json}

    CRITICAL RULES:
    1. You must ONLY use exercise names exactly as they appear above
    2. Create exactly {sessions_per_week} training days
    3. Use ONLY these days: [{days_str}]
        - This ensures proper rest between high-intensity sessions
        - Do NOT use any other days
    4. Each session should fit within the time constraint
    5. Follow proper exercise ordering: high intensity → lower intensity
    6. Include appropriate warm-up and cool-down

    Return a JSON object with ONLY a "weekly_schedule" array containing {sessions_per_week} days.
    Each day should have:
    - "day": Day of the week (must be one of: {days_str})
    - "focus": The exercise name(s) joined with " + " if multiple
    - "details": Detailed workout instructions including:
    - Warm-up protocol
    - Main exercises with sets, reps, rest periods
    - Cool-down
    - Total time estimate

    Example format:
    {{
        "weekly_schedule": [
            {{
                "day": "{training_days[0]}",
                "focus": "Fingerboard Max Hangs + Core Circuit",
                "details": "Warm-up: 15 min easy climbing, progressing to harder grades. Fingerboard Max Hangs: 5 sets of 10-second hangs on 18mm edge at 85% effort, 3 min rest between. Core Circuit: 3 rounds of 10 hanging knee raises, 30s plank, 10 Russian twists. Cool-down: 5 min easy traverse."
            }}
        ]
    }}

    Generate the weekly schedule now:
    """
        
        return prompt

    def _validate_phase_exercises(
        self, 
        phase_schedule: Dict[str, Any], 
        valid_names: List[str]
    ) -> Dict[str, Any]:
        """Validate and fix exercise names in a phase schedule."""
        from difflib import get_close_matches
        
        fixed_schedule = phase_schedule.copy()
        
        if "weekly_schedule" in fixed_schedule:
            for day in fixed_schedule["weekly_schedule"]:
                focus = day.get("focus", "")
                focus_parts = [part.strip() for part in focus.split("+")]
                fixed_parts = []
                
                for part in focus_parts:
                    if part in valid_names:
                        fixed_parts.append(part)
                    else:
                        # Try fuzzy matching
                        matches = get_close_matches(part, valid_names, n=1, cutoff=0.8)
                        if matches:
                            fixed_parts.append(matches[0])
                            logger.warning(f"Auto-fixed exercise: '{part}' -> '{matches[0]}'")
                        else:
                            logger.error(f"Invalid exercise '{part}' - no close match found")
                            # Skip this exercise
                
                if fixed_parts:
                    day["focus"] = " + ".join(fixed_parts)
        
        return fixed_schedule
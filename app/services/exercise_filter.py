# services/exercise_filter.py
import re
import logging
from collections import defaultdict
from typing import List, Dict, Any, Set
from app.models.training_plan import PhasePlanRequest
import app.db.db_access as db

logger = logging.getLogger(__name__)

class ExerciseFilterService:
    """Service for filtering and ranking exercises based on route and climber profile"""
    
    def parse_attribute_ratings(self, ratings_str: str) -> Dict[str, int]:
        """Parse the attribute ratings string into a dictionary of attribute -> rating."""
        if not ratings_str:
            return {}
        
        result = {}
        for item in ratings_str.split(", "):
            if ":" in item:
                attr, rating = item.split(":", 1)
                try:
                    result[attr.strip()] = int(rating.strip())
                except ValueError:
                    pass  # Skip if rating isn't an integer
        
        return result
    
    def parse_available_facilities(self, facilities_str: str) -> Set[str]:
        if not facilities_str or facilities_str.lower() in ["none", "n/a", ""]:
            return {
                "bouldering_wall",
                "fingerboard",
                "campus_board",
                "pullup_bar",
                "climbing_board",
                "circuit_board",
            }

        standard = {
            "bouldering_wall", "lead_wall", "fingerboard",
            "campus_board", "pullup_bar", "climbing_board",
            "spray_wall", "circuit_board", "weights",
        }

        out = set()
        for raw in facilities_str.split(","):
            # normalize into snake_case
            key = (
                raw.strip()
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
            )
            if key in standard:
                out.add(key)

        # ensure at least one wall facility
        if not out.intersection({
            "bouldering_wall",
            "lead_wall",
            "spray_wall",
            "circuit_board",
            "climbing_board"
        }):
            out.add("bouldering_wall")

        return out

    
    def get_phase_weights(self, phase_type: str, route_features: Dict[str, Any], attribute_ratings: Dict[str, int]) -> Dict[str, int]:
        """Get phase weights adjusted for route type and climber weaknesses."""
        
        # Base weights for different phase types
        base_weights = {
            "base":  {"strength": +3, "anaerobic_capacity": +2, "aerobic_capacity": +1, "power": 0},
            "peak":  {"anaerobic_power": +2, "aerobic_power": +2, "power": +1, "strength": 0, 
                      "anaerobic_capacity": -1, "aerobic_capacity": -1},
            "taper": {"strength": -1, "power": -1, "aerobic_capacity": 0},
        }
        
        weights = base_weights.get(phase_type, {}).copy()
        
        # ADJUSTMENTS for endurance routes with endurance weakness
        if route_features.get("is_endurance", False):
            endurance_rating = attribute_ratings.get("endurance", 3)
            
            if endurance_rating <= 2:  # Weak in endurance
                if phase_type == "base":
                    # Heavily prioritize building aerobic base
                    weights["aerobic_capacity"] += 5  # was +1, now +6 total
                    weights["strength"] -= 1  # was +3, now +2 total
                    
                elif phase_type == "peak":
                    # Focus on power-endurance
                    weights["aerobic_power"] += 4  # was +2, now +6 total
                    weights["anaerobic_power"] += 2  # was +2, now +4 total
                    weights["aerobic_capacity"] = 0  # was -1, now 0 (maintain)
        
        # For power routes with power weakness
        elif route_features.get("is_power", False):
            power_rating = attribute_ratings.get("power", 3)
            
            if power_rating <= 2:  # Weak in power
                if phase_type == "base":
                    weights["strength"] += 2  # Extra strength focus
                    weights["power"] += 2
                elif phase_type == "peak":
                    weights["power"] += 3
                    weights["anaerobic_power"] += 1
        
        return weights
    
    def filter_exercises_enhanced(self, exercises: List[Dict[str, Any]], data: PhasePlanRequest, route_features: Dict[str, Any], phase_type: str, phase_weeks: int) -> List[Dict[str, Any]]:
        """
        Enhanced filter with exercise ranking based on route and climber profile.
        Returns exercises filtered and sorted by relevance.
        """
        # Parse available facilities
        available_facilities = self.parse_available_facilities(data.training_facilities)
        logger.debug(f"Available facilities: {available_facilities}")
        
        # Get session time in minutes (convert from hours)
        session_time_str = data.time_per_session
        session_time_minutes = 120  # Default to 2 hours
        
        # Try to extract the numeric time value
        time_match = re.search(r'(\d+(?:\.\d+)?)', session_time_str)
        if time_match:
            time_value = float(time_match.group(1))
            # Check if it's specified in hours or minutes
            if "hour" in session_time_str.lower():
                session_time_minutes = int(time_value * 60)
            elif "minute" in session_time_str.lower() or "min" in session_time_str.lower():
                session_time_minutes = int(time_value)
            else:
                session_time_minutes = int(time_value * 60)
        
        logger.debug(f"Session time: {session_time_minutes} minutes")

        # Parse user ability levels
        boulder_grade = data.max_boulder_grade.upper().strip()
        climbing_grade = data.current_climbing_grade.lower().strip()

        # Simple parse: "V5+" → 5, "V4" → 4, else None
        m = re.match(r"V(\d+)", boulder_grade)
        boulder_grade_value = int(m.group(1)) if m else None

        # ————————————————
        # AGE RESTRICTION
        # ————————————————
        user_age = data.age  # Optional[int]

        # ————————————————
        # EXPERIENCE LEVEL (years_exp only)
        # ————————————————

        if data.years_experience is not None:
            years_exp = data.years_experience
        else:
            m = re.search(r'(\d+)\s*(?:year|yr)', data.training_experience.lower())
            years_exp = float(m.group(1)) if m else None

        if years_exp is not None:
            if years_exp < 1:
                experience_level = "beginner"
            elif years_exp >= 5:
                experience_level = "advanced"
            else:
                experience_level = "intermediate"
        else:
            # fallback keyword parse only if years_exp is missing
            txt = data.training_experience.lower()
            if any(t in txt for t in ["beginner","novice","starting","<1 year"]):
                experience_level = "beginner"
            elif any(t in txt for t in ["advanced","expert","many years"]):
                experience_level = "advanced"
            else:
                experience_level = "intermediate"
        
        # Parse attribute ratings for weaknesses and strengths
        attribute_ratings = self.parse_attribute_ratings(data.attribute_ratings)
        
        # Extract strengths and weaknesses
        strengths = set()
        weaknesses = set()
        
        # From attribute ratings (rated 1-2 = weakness, 4-5 = strength)
        if attribute_ratings:
            for attr, rating in attribute_ratings.items():
                attr_lower = attr.lower()
                if rating <= 2:  # weakness
                    weaknesses.add(attr_lower)
                elif rating >= 4:  # strength
                    strengths.add(attr_lower)
        
        # Also parse from text fields
        if data.perceived_strengths:
            for strength in data.perceived_strengths.lower().split(","):
                strengths.add(strength.strip())
        
        if data.perceived_weaknesses:
            for weakness in data.perceived_weaknesses.lower().split(","):
                weaknesses.add(weakness.strip())
        
        # Exercise categorization by safety concerns and type
        campus_exercises = {"Campus Board Exercises"}
        fingerboard_exercises = {"Fingerboard Max Hangs", "Fingerboard Repeater Blocks", "Fingerboard Max Hangs (Crimps)", "Fingerboard Max Hangs (Pockets)", "Fingerboard Max Hangs (Slopers)", "Fingerboard Max Hangs (Drag)"}
        power_exercises = {"Max Boulder Sessions", "Short Boulder Repeats", "Explosive Pull-Ups", "Broken Circuits"}
        endurance_exercises = {"Continuous Low-Intensity Climbing", "Route 4x4s", "Linked Laps", "X-On, X-Off Intervals", "Mixed Intensity Laps"}
        technique_exercises = {"Silent Feet Drills", "Flagging Practice", "High-Step Drills", "Slow Climbing", "Cross-Through Drills", "Open-Hand Grip Practice"}
        pocket_exercises = {"Fingerboard Max Hangs (Pockets)"}
        
        # Define exercise compatibility
        exercise_compatibility = {
            "Fingerboard Max Hangs": ["Dead Hangs", "Max Boulder Sessions"],
            "Boulder 4x4s": ["Linked Bouldering Circuits", "On-The-Minute Bouldering", "Silent Feet Drills"],
            "Continuous Low-Intensity Climbing": ["Silent Feet Drills", "Open-Hand Grip Practice"],
            "Route 4x4s": ["Linked Laps", "Boulder 4x4s"],
            "Max Boulder Sessions": ["Fingerboard Max Hangs", "Silent Feet Drills"],
            "Silent Feet Drills": ["High-Step Drills", "Cross-Through Drills"]
        }
        
        # Process and rank exercises
        ranked_exercises = []
        
        for ex in exercises:
            # Create a copy to avoid modifying original
            ex = ex.copy()
            ex_name = ex["name"]
            ex_type = ex["type"].lower()
            
            # Filter out exercises that require facilities the user doesn't have
            required_facilities = set(ex.get("required_facilities", "bouldering_wall").split(","))
            
            # Check if all required facilities are available
            if not required_facilities.issubset(available_facilities):
                # Skip this exercise if the user doesn't have the required facilities
                missing = required_facilities - available_facilities
                logger.debug(f"Skipping {ex_name} due to missing facilities: {missing}")
                continue
            
            # Check if the exercise takes too much time for the user's sessions
            time_required = int(ex.get("time_required", 30))
            if time_required > session_time_minutes:
                logger.debug(f"Skipping {ex_name} because it takes {time_required} minutes but session is only {session_time_minutes} minutes")
                continue
                
            # Initialize score
            score = 0
            ex["score"] = 0
            ex["compatible_with"] = exercise_compatibility.get(ex_name, [])
            
            # SAFETY FILTERS - Skip unsafe exercises            
            # No campus board if UNDER 18
            if ex_name in campus_exercises and user_age is not None and user_age < 18:
                continue

            # No campus board if too little experience or too low grade
            if ex_name in campus_exercises and (experience_level == "beginner" or (boulder_grade_value or 0) < 5):
                continue

            # No fingerboard if too little experience or too low grade
            if ex_name in fingerboard_exercises and (experience_level == "beginner" or (boulder_grade_value or 0) < 4):
                continue

            # ROUTE‐SPECIFIC FILTER: if no pocket feature, skip pocket‐only hangs
            if "pocket" in ex_name.lower() and not route_features.get("is_pockety", False):
                continue

            
            # SCORING SYSTEM
            
            # 1. Route-specific relevance (INCREASED SCORES)
            if route_features.get("is_endurance", False) and ex_name in endurance_exercises:
                score += 8  # was 5
                
            if route_features.get("is_power", False) and ex_name in power_exercises:
                score += 8  # was 5
                
            if route_features.get("is_technical", False) and ex_name in technique_exercises:
                score += 6  # was 5
            
            if route_features.get("is_crimpy", False) and ex_name in fingerboard_exercises:
                score += 4
                
            # Add scoring for pocket-specific routes
            if route_features.get("is_pockety", False) and ex_name in pocket_exercises:
                score += 5
                # Add pocket training notes to fingerboard exercises
                if "Fingerboard" in ex_name:
                    ex["description"] += " POCKET FOCUS: Include some training on pocket holds or mono/duo pockets if available."
            
            # 2. Addressing weaknesses (high priority)
            weakness_keywords = {
                "finger": {"Fingerboard Max Hangs", "Fingerboard Repeater Blocks", "Low Intensity Fingerboarding", "Dead Hangs", "Density Hangs"},
                "power": power_exercises,
                "strength": {"Max Boulder Sessions", "Weighted Pull-Ups", "One-Arm Lock-Offs", "Front Lever Progressions"},
                "endurance": endurance_exercises,
                "technique": technique_exercises,
                "crimp": fingerboard_exercises,
                "pocket": pocket_exercises,
            }
            
            for keyword, related_exercises in weakness_keywords.items():
                if any(keyword in w for w in weaknesses) and ex_name in related_exercises:
                    score += 6  # was 4
                    break
            
            # 3. Essential exercises (must include) - ADJUSTED FOR ROUTE TYPE
            if route_features.get("is_endurance", False):
                # Endurance route essentials
                essential_exercises = {
                    "Continuous Low-Intensity Climbing": 4,  # Highest priority
                    "Route 4x4s": 3,
                    "Boulder 4x4s": 3,
                    "Linked Laps": 3,
                    "X-On, X-Off Intervals": 2,
                    "Fingerboard Max Hangs": 1,  # Still include but lower priority
                    "Max Boulder Sessions": 1,
                }
            elif route_features.get("is_power", False):
                # Power route essentials
                essential_exercises = {
                    "Fingerboard Max Hangs": 4,
                    "Max Boulder Sessions": 4,
                    "Campus Board Exercises": 3,
                    "Board Sessions": 3,
                    "Boulder Pyramids": 2,
                    "Short Boulder Repeats": 2,
                }
            else:
                # Balanced route essentials
                essential_exercises = {
                    "Fingerboard Max Hangs": 3,
                    "Max Boulder Sessions": 3,
                    "Board Sessions": 3,
                    "Boulder Pyramids": 2,
                    "Boulder 4x4s": 2,
                    "Continuous Low-Intensity Climbing": 2
                }
            
            if ex_name in essential_exercises:
                score += essential_exercises[ex_name]
            
            # 4. Priority from the exercise definition
            if ex.get("priority") == "high":
                score += 3
            elif ex.get("priority") == "medium":
                score += 2
                
            # 5. Experience level appropriateness
            if experience_level == "beginner" and ex_type in ["technique", "aerobic_capacity"]:
                score += 2
                
            if experience_level == "advanced" and ex_type in ["strength", "power"]:
                score += 1
                
            # 6. Time efficiency bonus - shorter exercises get a small boost
            if time_required < 30:
                score += 1
            
            # Record the final score and time requirement
            ex["time_required"] = time_required
            
            # Phase-based adjustment (must happen before we decide inclusion)
            # Use the new get_phase_weights method
            phase_weights = self.get_phase_weights(phase_type, route_features, attribute_ratings)
            score += phase_weights.get(ex_type, 0)

            # Record the final score and include only positive-scoring exercises
            ex["score"] = score
            if score > 0:
                ranked_exercises.append(ex)

        # Sort by score (descending)
        ranked_exercises.sort(key=lambda x: x["score"], reverse=True)

        # 1) Bucket by system
        buckets = defaultdict(list)
        for ex in ranked_exercises:
            buckets[ex["type"]].append(ex)

        # 2) Reserve one per critical system
        critical_systems = [
            "strength",
            "anaerobic_capacity",
            "aerobic_capacity",
            "anaerobic_power",
            "aerobic_power",
        ]
        final_list = []

        for sys in critical_systems:
            if buckets[sys]:
                # take the top-scoring exercise of that type
                final_list.append(buckets[sys][0])

        # 3) Fill the remainder up to your target (e.g. 12–15)
        TARGET_COUNT = 15
        for ex in ranked_exercises:
            if len(final_list) >= TARGET_COUNT:
                break
            if ex not in final_list:
                final_list.append(ex)

        # 4) Use this balanced list from here on
        ranked_exercises = final_list
        
        return ranked_exercises
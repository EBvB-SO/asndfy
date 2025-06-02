# services/exercise_filter.py
import re
import logging
from typing import List, Dict, Any, Set
from models.training_plan import PhasePlanRequest
import db.db_access as db

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
        """Parse a comma-separated facilities string into a set of available facilities."""
        if not facilities_str or facilities_str.lower() in ["none", "n/a", ""]:
            # Default facilities if none specified
            return set([
                "bouldering_wall", 
                "lead_wall", 
                "fingerboard", 
                "campus_board", 
                "pullup_bar", 
                "climbing_board",
                "spray_wall",
                "circuit_board",
                "weights"
            ])
        
        # Parse the user's input
        facilities = set()
        
        # Standard facility names used in the app
        standard_facilities = {
            "bouldering_wall", 
            "lead_wall", 
            "fingerboard", 
            "campus_board", 
            "pullup_bar", 
            "climbing_board",
            "spray_wall",
            "circuit_board",
            "weights"
        }
        
        # Split by commas and process each facility
        for facility in facilities_str.split(","):
            facility = facility.strip().lower()
            
            # Direct match with standard names
            if facility in standard_facilities:
                facilities.add(facility)
        
        # Always include at least a bouldering wall if nothing else is specified
        if not any(facility in facilities for facility in ["bouldering_wall", "lead_wall", "spray_wall", "circuit_board", "climbing_board"]):
            facilities.add("bouldering_wall")
        
        return facilities
    
    def filter_exercises_enhanced(self, exercises: List[Dict[str, Any]], data: PhasePlanRequest, route_features: Dict[str, Any]) -> List[Dict[str, Any]]:
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
        
        # Determine experience level
        experience_level = "intermediate"  # Default
        
        # Look for explicit mentions in training_experience
        experience_text = data.training_experience.lower()
        if any(term in experience_text for term in ["beginner", "novice", "new", "starting", "less than a year"]):
            experience_level = "beginner"
        elif any(term in experience_text for term in ["advanced", "expert", "experienced", "many years", "over 5 years"]):
            experience_level = "advanced"
        
        # Parse for numerical indicators
        years_match = re.search(r'(\d+)\s*(?:year|yr)', experience_text)
        if years_match:
            years = int(years_match.group(1))
            if years < 1:
                experience_level = "beginner"
            elif years >= 5:
                experience_level = "advanced"
        
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
        campus_exercises = {"Campus Board Exercises", "Campus Laddering", "Intensive Foot-On Campus"}
        fingerboard_exercises = {"Fingerboard Max Hangs", "Fingerboard Repeater Blocks", "Low Intensity Fingerboarding", "Density Hangs"}
        power_exercises = {"Max Boulder Sessions", "Short Boulder Repeats", "Explosive Pull-Ups", "Broken Circuits"}
        endurance_exercises = {"Continuous Low-Intensity Climbing", "Route 4x4s", "Linked Laps", "X-On, X-Off Intervals", "Mixed Intensity Laps"}
        technique_exercises = {"Silent Feet Drills", "Flagging Practice", "High-Step Drills", "Slow Climbing", "Cross-Through Drills", "Open-Hand Grip Practice"}
        pocket_exercises = {"Fingerboard Max Hangs", "Fingerboard Repeater Blocks", "Density Hangs"}
        
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
            if ex_name in campus_exercises:
                # Only allow campus exercises for advanced climbers or 7a+ climbers
                if experience_level == "beginner" or "7" not in climbing_grade:
                    continue
            
            # Make fingerboard exercises safer for beginners
            if experience_level == "beginner" and ex_name in fingerboard_exercises:
                ex["description"] = "BEGINNER MODIFICATION: " + ex["description"]
                if "Max Hangs" in ex_name:
                    ex["description"] += " Use larger edges (20mm+) and reduced load."
            
            # SCORING SYSTEM
            
            # 1. Route-specific relevance
            if route_features.get("is_endurance", False) and ex_name in endurance_exercises:
                score += 5
            
            if route_features.get("is_power", False) and ex_name in power_exercises:
                score += 5
            
            if route_features.get("is_technical", False) and ex_name in technique_exercises:
                score += 5
            
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
                    score += 4
                    break
            
            # 3. Essential exercises (must include)
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
            ex["score"] = score
            ex["time_required"] = time_required
            
            # Only include if it has a positive score (relevant)
            if score > 0:
                ranked_exercises.append(ex)
        
        # Sort by score (descending)
        ranked_exercises.sort(key=lambda x: x["score"], reverse=True)
        
        # Ensure we have enough exercises (minimum 12)
        if len(ranked_exercises) < 12:
            # Add more exercises that weren't included
            for ex in exercises:
                ex_copy = ex.copy()
                ex_copy["score"] = 0
                time_required = int(ex.get("time_required", 30))
                ex_copy["time_required"] = time_required
                
                # Check facility requirements and time requirements here too
                required_facilities = set(ex.get("required_facilities", "bouldering_wall").split(","))
                if (ex["name"] not in [e["name"] for e in ranked_exercises] 
                    and required_facilities.issubset(available_facilities)
                    and time_required <= session_time_minutes):
                    ranked_exercises.append(ex_copy)
                    if len(ranked_exercises) >= 15:
                        break
        
        return ranked_exercises
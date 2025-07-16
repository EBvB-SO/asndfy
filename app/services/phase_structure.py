# app/services/phase_structure.py
import logging
from typing import List, Dict, Any, Tuple
from app.models.training_plan import PhasePlanRequest

logger = logging.getLogger(__name__)


class PhaseStructureService:
    """Service for determining training plan phase structure based on climber profile and route demands."""
    
    def __init__(self):
        # Phase allocation rules can be configured here
        self.MIN_STRENGTH_PHASE_WEEKS = 2
        self.MIN_TAPER_WEEKS = 1
        
    def _parse_years_from_text(self, experience_text: str) -> float:
        """Extract years of experience from text description."""
        import re
        if not experience_text:
            return 0
        
        text_lower = experience_text.lower()
        match = re.search(r'(\d+)\s*(?:year|yr)', text_lower)
        if match:
            return float(match.group(1))
        
        # Keyword fallbacks
        if any(term in text_lower for term in ["beginner", "novice", "starting", "<1 year"]):
            return 0.5
        elif any(term in text_lower for term in ["advanced", "expert", "many years"]):
            return 5.0
        else:
            return 2.0  # Default to intermediate
    
    def _analyze_climber_needs(self, data: PhasePlanRequest, attribute_ratings: Dict[str, int]) -> Dict[str, bool]:
        """Determine what the climber needs to work on."""
        needs = {
            "strength": False,
            "endurance": False,
            "power_endurance": False,
            "technique": False
        }
        
        # Check ratings (1-2 = weakness, 3 = neutral, 4-5 = strength)
        if attribute_ratings:
            needs["strength"] = (
                attribute_ratings.get("finger_strength", 3) <= 2 or
                attribute_ratings.get("power", 3) <= 2
            )
            needs["endurance"] = (
                attribute_ratings.get("endurance", 3) <= 2 or
                attribute_ratings.get("stamina", 3) <= 2
            )
            needs["power_endurance"] = attribute_ratings.get("power_endurance", 3) <= 2
        
        # Also check text descriptions
        weaknesses_lower = data.perceived_weaknesses.lower()
        needs["strength"] = needs["strength"] or any(
            term in weaknesses_lower for term in ["strength", "power", "finger", "crimp"]
        )
        needs["endurance"] = needs["endurance"] or any(
            term in weaknesses_lower for term in ["endurance", "pump", "stamina"]
        )
        needs["power_endurance"] = needs["power_endurance"] or any(
            term in weaknesses_lower for term in ["power endurance", "power-endurance"]
        )
        needs["technique"] = any(
            term in weaknesses_lower for term in ["technique", "footwork", "movement"]
        )
        
        return needs
    
    def get_training_days(self, sessions_per_week: int) -> List[str]:
        """
        Get the optimal training days for a given number of sessions per week.
        Ensures proper rest between high-intensity sessions.
        """
        schedules = {
            2: ["Tuesday", "Friday"],
            3: ["Monday", "Wednesday", "Friday"],
            4: ["Monday", "Tuesday", "Thursday", "Saturday"],
            5: ["Monday", "Tuesday", "Thursday", "Friday", "Saturday"],
            6: ["Monday", "Tuesday", "Wednesday", "Friday", "Saturday", "Sunday"],
        }
        
        return schedules.get(sessions_per_week, ["Monday", "Wednesday", "Friday"])
    
    def determine_phase_structure(
        self, 
        data: PhasePlanRequest, 
        weeks: int, 
        sessions_per_week: int, 
        route_features: Dict[str, Any],
        attribute_ratings: Dict[str, int]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Determine optimal phase structure based on all factors.
        
        Returns list of phase dictionaries with:
        - name: Human-readable phase name
        - type: "base", "peak", or "taper"
        - weeks: Duration of phase
        - description: What this phase focuses on

        Returns tuple of (phases, training_days) where:
        - phases: List of phase dictionaries
        - training_days: List of days of the week to train on
        """
        phases = []
        training_days = self.get_training_days(sessions_per_week)
        
        # Analyze climber profile
        years_exp = data.years_experience or self._parse_years_from_text(data.training_experience)
        is_beginner = years_exp < 1
        is_advanced = years_exp >= 5
        
        # Determine needs
        needs = self._analyze_climber_needs(data, attribute_ratings)
        
        # Route characteristics
        route_is_endurance = (
            route_features.get("is_endurance", False) or
            "long" in data.route_lengths.lower()
        )
        route_is_power = (
            route_features.get("is_power", False) or
            "bouldery" in data.route_lengths.lower() or
            "short" in data.route_lengths.lower()
        )
        route_is_technical = route_features.get("is_technical", False)
        
        # PHASE ALLOCATION LOGIC
        if weeks <= 4:
            phases.extend(self._create_short_plan(
                weeks, needs, route_is_endurance, route_is_power
            ))
        elif weeks <= 8:
            phases.extend(self._create_medium_plan(
                weeks, needs, route_is_endurance, route_is_power, is_beginner
            ))
        else:
            phases.extend(self._create_long_plan(
                weeks, needs, route_is_endurance, route_is_power, is_beginner
            ))
        
        # Log the phase structure for debugging
        logger.info(f"Generated phase structure for {weeks} weeks: {[p['name'] for p in phases]}")
        
        return phases, training_days
    
    def _create_short_plan(
        self, weeks: int, needs: Dict[str, bool], 
        route_is_endurance: bool, route_is_power: bool
    ) -> List[Dict[str, Any]]:
        """Create phases for plans 4 weeks or shorter."""
        if route_is_endurance and not needs["strength"]:
            return [{
                "name": f"Power-Endurance Focus (Weeks 1-{weeks})",
                "type": "peak",
                "weeks": weeks,
                "description": "Compressed preparation focusing on route-specific endurance with minimal strength work"
            }]
        elif route_is_power or needs["strength"]:
            return [{
                "name": f"Strength & Power (Weeks 1-{weeks})",
                "type": "base",
                "weeks": weeks,
                "description": "Intensive strength and power development for short-term gains"
            }]
        else:
            # Balanced approach for mixed routes
            return [{
                "name": f"Integrated Training (Weeks 1-{weeks})",
                "type": "base",
                "weeks": weeks,
                "description": "Combined strength and endurance work for well-rounded preparation"
            }]
    
    def _create_medium_plan(
        self, weeks: int, needs: Dict[str, bool],
        route_is_endurance: bool, route_is_power: bool, is_beginner: bool
    ) -> List[Dict[str, Any]]:
        """Create phases for 5-8 week plans."""
        base_weeks = weeks // 2
        peak_weeks = weeks - base_weeks
        
        phases = []
        
        if route_is_endurance and needs["endurance"]:
            # Split more evenly to allow adequate endurance development
            if weeks <= 6:
                base_weeks = weeks // 2
                peak_weeks = weeks - base_weeks
            else:
                # For 7-8 weeks, give more time to peak phase for endurance
                base_weeks = 3
                peak_weeks = weeks - base_weeks
            
            phases.extend([
                {
                    "name": f"Aerobic Base Building (Weeks 1-{base_weeks})",
                    "type": "base",
                    "weeks": base_weeks,
                    "description": "Build aerobic capacity and climbing volume. Focus on continuous climbing, ARC training, and building a strong endurance foundation while maintaining finger strength."
                },
                {
                    "name": f"Power-Endurance Development (Weeks {base_weeks+1}-{weeks})",
                    "type": "peak",
                    "weeks": peak_weeks,
                    "description": "Transition to route-specific power-endurance. Focus on 4x4s, intervals, and sustained climbing at higher intensities to match route demands."
                }
            ])
        elif route_is_endurance and not needs["strength"]:
            # Original logic for endurance routes when already strong
            base_weeks = weeks // 2
            peak_weeks = weeks - base_weeks
            
            phases.extend([
                {
                    "name": f"Base Conditioning (Weeks 1-{base_weeks})",
                    "type": "base",
                    "weeks": base_weeks,
                    "description": "Build aerobic capacity and refine movement efficiency"
                },
                {
                    "name": f"Route-Specific Endurance (Weeks {base_weeks+1}-{weeks})",
                    "type": "peak",
                    "weeks": peak_weeks,
                    "description": "Transition to route-specific power-endurance and pacing"
                }
            ])
        elif route_is_power or needs["strength"]:
            phases.extend([
                {
                    "name": f"Strength & Power (Weeks 1-{base_weeks})",
                    "type": "base",
                    "weeks": base_weeks,
                    "description": "Maximum strength and power development"
                },
                {
                    "name": f"Power Application (Weeks {base_weeks+1}-{weeks})",
                    "type": "peak",
                    "weeks": peak_weeks,
                    "description": "Convert raw strength to climbing-specific power"
                }
            ])
        else:
            # Standard periodization
            phases.extend([
                {
                    "name": f"Foundation (Weeks 1-{base_weeks})",
                    "type": "base",
                    "weeks": base_weeks,
                    "description": "Build strength base while maintaining endurance"
                },
                {
                    "name": f"Route Preparation (Weeks {base_weeks+1}-{weeks})",
                    "type": "peak",
                    "weeks": peak_weeks,
                    "description": "Shift focus to route-specific demands"
                }
            ])
        
        return phases
    
    def _create_long_plan(
        self, weeks: int, needs: Dict[str, bool],
        route_is_endurance: bool, route_is_power: bool, is_beginner: bool
    ) -> List[Dict[str, Any]]:
        """Create phases for plans longer than 8 weeks."""
        phases = []
        taper_weeks = 1 if weeks >= 10 else 0
        remaining_weeks = weeks - taper_weeks
        
        if weeks >= 16:
            # Very long plan - add a deload week
            deload_week = weeks // 2
            
        if route_is_endurance and not needs["strength"]:
            # Endurance-focused progression
            if remaining_weeks >= 12:
                base1_weeks = remaining_weeks // 4
                base2_weeks = remaining_weeks // 4
                peak1_weeks = remaining_weeks // 4
                peak2_weeks = remaining_weeks - base1_weeks - base2_weeks - peak1_weeks
                
                phases.extend([
                    {
                        "name": f"Aerobic Base (Weeks 1-{base1_weeks})",
                        "type": "base",
                        "weeks": base1_weeks,
                        "description": "Develop foundational aerobic capacity"
                    },
                    {
                        "name": f"Volume Building (Weeks {base1_weeks+1}-{base1_weeks+base2_weeks})",
                        "type": "base",
                        "weeks": base2_weeks,
                        "description": "Increase climbing volume and work capacity"
                    },
                    {
                        "name": f"Power-Endurance (Weeks {base1_weeks+base2_weeks+1}-{base1_weeks+base2_weeks+peak1_weeks})",
                        "type": "peak",
                        "weeks": peak1_weeks,
                        "description": "Develop sustained power output"
                    },
                    {
                        "name": f"Route Simulation (Weeks {base1_weeks+base2_weeks+peak1_weeks+1}-{weeks-taper_weeks})",
                        "type": "peak",
                        "weeks": peak2_weeks,
                        "description": "Route-specific preparation and tactics"
                    }
                ])
            else:
                # Shorter long plan (9-11 weeks)
                base_weeks = remaining_weeks * 4 // 10
                build_weeks = remaining_weeks * 3 // 10
                peak_weeks = remaining_weeks - base_weeks - build_weeks
                
                phases.extend([
                    {
                        "name": f"Base Phase (Weeks 1-{base_weeks})",
                        "type": "base",
                        "weeks": base_weeks,
                        "description": "Aerobic development and movement quality"
                    },
                    {
                        "name": f"Build Phase (Weeks {base_weeks+1}-{base_weeks+build_weeks})",
                        "type": "base",
                        "weeks": build_weeks,
                        "description": "Increase intensity and introduce power-endurance"
                    },
                    {
                        "name": f"Peak Phase (Weeks {base_weeks+build_weeks+1}-{weeks-taper_weeks})",
                        "type": "peak",
                        "weeks": peak_weeks,
                        "description": "Route-specific fitness and performance"
                    }
                ])
        else:
            # Standard or power-focused progression
            base_weeks = remaining_weeks * 4 // 10  # 40%
            transition_weeks = remaining_weeks * 2 // 10  # 20%
            peak_weeks = remaining_weeks - base_weeks - transition_weeks  # 40%
            
            phases.extend([
                {
                    "name": f"Strength & Power (Weeks 1-{base_weeks})",
                    "type": "base",
                    "weeks": base_weeks,
                    "description": "Maximum strength and power development"
                },
                {
                    "name": f"Power-Endurance Transition (Weeks {base_weeks+1}-{base_weeks+transition_weeks})",
                    "type": "base",
                    "weeks": transition_weeks,
                    "description": "Bridge strength gains to climbing fitness"
                },
                {
                    "name": f"Route-Specific Preparation (Weeks {base_weeks+transition_weeks+1}-{weeks-taper_weeks})",
                    "type": "peak",
                    "weeks": peak_weeks,
                    "description": "Apply fitness to route-specific demands"
                }
            ])
        
        # Add taper if applicable
        if taper_weeks > 0:
            phases.append({
                "name": f"Taper & Peak (Week {weeks})",
                "type": "taper",
                "weeks": taper_weeks,
                "description": "Reduce volume by 40-50%, maintain intensity, optimize for performance"
            })
        
        return phases
#!/usr/bin/env python3
import os, sys

# make sure the parent dir (the one that contains `app/`) is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import json
from app.services.plan_generator import PlanGeneratorService
from app.models.training_plan import PhasePlanRequest, FullPlanRequest

def make_phase_request() -> PhasePlanRequest:
    return PhasePlanRequest(
        route="Sample Route",
        grade="7b",
        crag="Sample Crag",
        route_angles="Overhanging",
        route_lengths="Long",
        hold_types="Crimpy",
        route_description="Sustained crimpy climbing with a hard crux near the top",
        weeks_to_train="8",
        sessions_per_week="4",
        time_per_session="2 hours",
        current_climbing_grade="7a",
        max_boulder_grade="V6",
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

def main():
    service = PlanGeneratorService()

    # ---- Preview ----
    req = make_phase_request()
    print("=== ROUTE PREVIEW ===")
    preview = service.generate_preview(req)
    print(json.dumps(preview, indent=2))

    # ---- Full Plan ----
    full_req = FullPlanRequest(
        plan_data=req,
        weeks_to_train=int(req.weeks_to_train),
        sessions_per_week=int(req.sessions_per_week),
    )
    print("\n=== FULL PLAN ===")
    full = service.generate_full_plan(full_req)
    print(json.dumps(full, indent=2))

if __name__ == "__main__":
    main()

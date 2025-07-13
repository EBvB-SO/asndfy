#!/usr/bin/env python3
"""
Quick diagnostic script to check PlanGeneratorService setup.
Run this to identify specific issues with the refactored code.
"""
import os
import sys

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def diagnose():
    print("🔍 Diagnosing PlanGeneratorService Setup")
    print("=" * 50)
    
    # Step 1: Check imports
    print("\n1. Checking imports...")
    try:
        from app.services import plan_generator
        print("  ✅ Can import plan_generator module")
    except ImportError as e:
        print(f"  ❌ Cannot import plan_generator: {e}")
        return
    
    try:
        from app.services.phase_structure import PhaseStructureService
        print("  ✅ Can import PhaseStructureService")
    except ImportError as e:
        print(f"  ❌ Cannot import PhaseStructureService: {e}")
        print("     Fix: Ensure app/services/phase_structure.py exists")
        return
    
    try:
        from app.services.exercise_filter import ExerciseFilterService
        print("  ✅ Can import ExerciseFilterService")
    except ImportError as e:
        print(f"  ❌ Cannot import ExerciseFilterService: {e}")
        return
    
    # Step 2: Check plan_generator.py contents
    print("\n2. Checking plan_generator.py contents...")
    plan_gen_path = os.path.join(
        os.path.dirname(__file__),
        "..", "app", "services", "plan_generator.py"
    )
    plan_gen_path = os.path.normpath(plan_gen_path)
    
    if not os.path.exists(plan_gen_path):
        print(f"  ❌ Cannot find plan_generator.py at {plan_gen_path}")
        return
    
    with open(plan_gen_path, 'r') as f:
        content = f.read()
    
    # a) phase_structure import
    has_phase_import = any(kw in content for kw in [
        "from services.phase_structure import PhaseStructureService",
        "from .phase_structure import PhaseStructureService",
        "from app.services.phase_structure import PhaseStructureService"
    ])
    print(f"  {'✅' if has_phase_import else '❌'} Has PhaseStructureService import")
    if not has_phase_import:
        print("     Fix: Add one of:")
        print("       from services.phase_structure import PhaseStructureService")
        print("       from .phase_structure import PhaseStructureService")
        print("       from app.services.phase_structure import PhaseStructureService")
    
    # b) exercise_filter import
    has_ex_import = any(kw in content for kw in [
        "from services.exercise_filter import ExerciseFilterService",
        "from .exercise_filter import ExerciseFilterService",
        "from app.services.exercise_filter import ExerciseFilterService"
    ])
    print(f"  {'✅' if has_ex_import else '❌'} Has ExerciseFilterService import")
    if not has_ex_import:
        print("     Fix: Add one of:")
        print("       from services.exercise_filter import ExerciseFilterService")
        print("       from .exercise_filter import ExerciseFilterService")
        print("       from app.services.exercise_filter import ExerciseFilterService")
    
    # c) self.phase_structure initialization
    has_phase_init = "self.phase_structure" in content
    print(f"  {'✅' if has_phase_init else '❌'} Initializes self.phase_structure in __init__")
    if not has_phase_init:
        print("     Fix: In PlanGeneratorService.__init__, add:")
        print("       self.phase_structure = PhaseStructureService()")
    
    # d) self.exercise_filter initialization
    has_ex_init = "self.exercise_filter" in content
    print(f"  {'✅' if has_ex_init else '❌'} Initializes self.exercise_filter in __init__")
    if not has_ex_init:
        print("     Fix: In PlanGeneratorService.__init__, add:")
        print("       self.exercise_filter = ExerciseFilterService()")
    
    print("\n✅ Diagnostic complete.")

if __name__ == "__main__":
    diagnose()

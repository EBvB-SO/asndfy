# scripts/init_database.py

import logging
import uuid
from app.core.database import SessionLocal
from app.db.models import Exercise, ExerciseTarget, BadgeCategory, Badge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_exercises():
    """Initialize the exercise library (exercises + any ExerciseTarget rows)."""
    db = SessionLocal()
    try:
        # If there is already at least one exercise in the table, skip initialization
        if db.query(Exercise).count() > 0:
            logger.info("Exercises already initialized, skipping.")
            return

        exercise_data = [
            # ————————————————
            # AERO CAP EXERCISES
            # ————————————————
            {
                "name": "Continuous Low-Intensity Climbing",
                "type": "aerobic_capacity",
                "description": "Stay on the wall continuously for 20-40 minutes at a comfortably easy grade. Focus on smooth technique, controlled breathing and minimal rest on holds.",
                "priority": "high",
                "time_required": 60,
                "required_facilities": "lead_wall,bouldering_wall,spray_wall,circuit_board"
            },
            {
                "name": "Mixed Intensity Laps",
                "type": "aerobic_capacity",
                "description": "Climb half of an easy route before switching into the second half of a more difficult route, completing 30-40 moves in total. Rest 8-12 minutes between sets.",
                "priority": "medium",
                "time_required": 90,
                "required_facilities": "lead_wall,bouldering_wall,spray_wall,circuit_board"
            },
            {
                "name": "X-On, X-Off Intervals",
                "type": "aerobic_capacity",
                "description": "Typically 10 minutes climbing, 10 minutes rest, repeated 3-4 times",
                "priority": "high",
                "time_required": 60,
                "required_facilities": "lead_wall,bouldering_wall,spray_wall,circuit_board"
            },
            {
                "name": "Route 4x4s",
                "type": "aerobic_capacity",
                "description": "Lead the same route 4 times with minimal rest between attempts",
                "priority": "high",
                "time_required": 60,
                "required_facilities": "lead_wall,circuit_board"
            },
            {
                "name": "Linked Laps",
                "type": "aerobic_capacity",
                "description": "Climb a moderate route, lower off, shake for ~1 minute, then climb again. Do 2-3 back-to-back laps.",
                "priority": "medium",
                "time_required": 30,
                "required_facilities": "lead_wall,circuit_board"
            },
            {
                "name": "Low Intensity Fingerboarding",
                "type": "aerobic_capacity",
                "description": "Using 30-40% of your maximum hang, complete a 7 second hang, followed by 3 seconds of rest, for 10-16 reps. Repeat for 6-10 sets with 1 minute of rest between each set.",
                "priority": "medium",
                "time_required": 30,
                "required_facilities": "fingerboard"
            },
            {
                "name": "Foot-On Campus Endurance",
                "type": "aerobic_capacity",
                "description": "Use a campus board with feet on lower rungs or small footholds. Move steadily for 5-10 minutes at a time, minimizing rests.",
                "priority": "medium",
                "time_required": 30,
                "required_facilities": "campus_board"
            },

            # ————————————————
            # AN CAP EXERCISES
            # ————————————————
            {
                "name": "Long Boulder Circuits",
                "type": "anaerobic_capacity",
                "description": "Set or find 12-15 move boulder problems or link sections on a training wall. Climb with effort, then rest 2-4 times the climbing duration.",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "bouldering_wall,spray_wall,circuit_board"
            },
            {
                "name": "Boulder Triples",
                "type": "anaerobic_capacity",
                "description": "Choose three challenging boulder problems around 6-8 moves long. For each set, climb one boulder three times in succession, resting exactly 60 seconds between repetitions.",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "bouldering_wall,spray_wall,circuit_board,climbing_board"
            },
            {
                "name": "Linked Bouldering Circuits",
                "type": "anaerobic_capacity",
                "description": "String together 2-3 boulder problems in one go. Avoid resting on the ground between them.",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "bouldering_wall,spray_wall,circuit_board,climbing_board"
            },
            {
                "name": "Campus Laddering",
                "type": "anaerobic_capacity",
                "description": "Use a campus board to move hand-over-hand up and down 15-20 moves per set. Rest 2-3 minutes between sets and do 8-10 sets total.",
                "priority": "medium",
                "time_required": 30,
                "required_facilities": "campus_board"
            },
            {
                "name": "Fingerboard Repeater Blocks",
                "type": "anaerobic_capacity",
                "description": "Perform 4 consecutive hangs of ~7 seconds on / 3 seconds off as one 'block.' Rest 2-3 minutes, then repeat for 3-5 blocks.",
                "priority": "medium",
                "time_required": 30,
                "required_facilities": "fingerboard"
            },
            {
                "name": "Multiple Set Boulder Circuits",
                "type": "anaerobic_capacity",
                "description": "Design a short circuit of linked boulder problems. Climb 4-5 repetitions, rest 10-20 minutes, then repeat 2-3 times.",
                "priority": "high",
                "time_required": 60,
                "required_facilities": "bouldering_wall,spray_wall,circuit_board"
            },
            {
                "name": "Density Hangs",
                "type": "anaerobic_capacity",
                "description": "On a fingerboard or good holds on the wall, hang for longer durations (20-40 seconds) at a moderately difficult load. Rest briefly and repeat.",
                "priority": "medium",
                "time_required": 20,
                "required_facilities": "fingerboard"
            },

            # ————————————————
            # AERO POW EXERCISES
            # ————————————————
            {
                "name": "30-Move Circuits",
                "type": "aerobic_power",
                "description": "Create a 30-move circuit on a training wall or link multiple problems without rests or shake-outs. Rest 1-2 times your climbing time between sets.",
                "priority": "high",
                "time_required": 30,
                "required_facilities": "bouldering_wall,spray_wall,circuit_board"
            },
            {
                "name": "On-The-Minute Bouldering",
                "type": "aerobic_power",
                "description": "Choose a short, ~6-8 move boulder problem. Start one attempt every minute on the minute (EMOM) for 8 total reps.",
                "priority": "high",
                "time_required": 30,
                "required_facilities": "bouldering_wall,spray_wall,circuit_board,climbing_board"
            },
            {
                "name": "Boulder 4x4s",
                "type": "aerobic_power",
                "description": "Pick 4 boulder problems around your onsight level or slightly below. Climb them back-to-back with minimal rest, then rest 1-3 minutes and repeat the entire 4-problem circuit a total of 4 times.",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "bouldering_wall,spray_wall,circuit_board,climbing_board"
            },
            {
                "name": "3x3 Bouldering Circuits",
                "type": "aerobic_power",
                "description": "Select 3 boulder problems at a challenging level. Climb each problem 3 times in a row with minimal rest, then rest more thoroughly and move to the next problem.",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "bouldering_wall,spray_wall,circuit_board,climbing_board"
            },
            {
                "name": "Intensive Foot-On Campus",
                "type": "aerobic_power",
                "description": "On a campus board, keep your feet on small rungs or designated footholds. Climb up and down for about 1 minute, then rest 1-2 minutes. Complete 8 reps total.",
                "priority": "high",
                "time_required": 20,
                "required_facilities": "campus_board"
            },

            # ————————————————
            # AN POW EXERCISES
            # ————————————————
            {
                "name": "Short Boulder Repeats",
                "type": "anaerobic_power",
                "description": "Select a ~5-7 move boulder problem near your max. Climb it 4 times with rest equal to or less than climbing time. Complete 4 total sets, resting about 10 minutes between each set.",
                "priority": "high",
                "time_required": 60,
                "required_facilities": "bouldering_wall,spray_wall,climbing_board"
            },
            {
                "name": "Broken Circuits",
                "type": "anaerobic_power",
                "description": "Create a ~25-move circuit and break it into 3-4 sections. Climb each section quickly with minimal rest between sections.",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "bouldering_wall,spray_wall,circuit_board,climbing_board"
            },
            {
                "name": "Max Intensity Redpoints",
                "type": "anaerobic_power",
                "description": "Work on a ~20-30 move route or circuit at your absolute limit. Attempt full redpoints with proper rest (10+ minutes) between tries.",
                "priority": "medium",
                "time_required": 60,
                "required_facilities": "lead_wall,bouldering_wall,circuit_board,climbing_board"
            },

            # ————————————————
            # STRENGTH Exercises
            # ————————————————
            {
                "name": "Max Boulder Sessions",
                "type": "strength",
                "description": "Work on your hardest boulder problems with full rest (3-5 minutes) between tries. Emphasize precision and maximum effort.",
                "priority": "high",
                "time_required": 60,
                "required_facilities": "bouldering_wall,spray_wall,climbing_board"
            },
            {
                "name": "Board Session",
                "type": "strength",
                "description": "Hard boulder problems on a board. Start easy and slowly progress through 10 boulders getting harder and harder",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "spray_wall,climbing_board"
            },
            {
                "name": "Boulder Pyramids",
                "type": "strength",
                "description": "Attempting 8 different boulders ranging from hard to maximum effort",
                "priority": "high",
                "time_required": 60,
                "required_facilities": "bouldering_wall,spray_wall,climbing_board"
            },
            {
                "name": "Boulder Intervals",
                "type": "strength",
                "description": "Climb 5 boulders 3 times with 3 minutes rest between attempts",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "bouldering_wall,spray_wall,climbing_board"
            },
            {
                "name": "Volume Bouldering",
                "type": "strength",
                "description": "Climb 15 boulder problems of moderate difficulty in 45 minutes",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "bouldering_wall,spray_wall,climbing_board"
            },
            {
                "name": "Fingerboard Max Hangs",
                "type": "strength",
                "description": "Choose a small edge or add weight so that a 10-second hang is near your limit. After each hang, rest fully (2-3 minutes).",
                "priority": "high",
                "time_required": 30,
                "required_facilities": "fingerboard"
            },
            {
                "name": "Dead Hangs",
                "type": "strength",
                "description": "Simply hang on a pull-up bar, jugs, or fingerboard edges for ~20-30 seconds. Rest briefly and repeat for multiple sets.",
                "priority": "medium",
                "time_required": 15,
                "required_facilities": "fingerboard,pullup_bar"
            },
            {
                "name": "Weighted Pull-Ups",
                "type": "strength",
                "description": "Attach a weight belt or hold a dumbbell between your feet. Perform pull-ups in sets of 3-8 reps, resting 2-3 minutes.",
                "priority": "medium",
                "time_required": 20,
                "required_facilities": "fingerboard,pullup_bar"
            },
            {
                "name": "One-Arm Lock-Offs",
                "type": "strength",
                "description": "Use a pull-up bar or a ring. Pull up with both arms, then remove one arm and hold a lock-off for a few seconds. Lower slowly.",
                "priority": "medium",
                "time_required": 20,
                "required_facilities": "fingerboard,pullup_bar"
            },

            # ————————————————
            # POWER EXERCISES
            # ————————————————
            {
                "name": "Campus Board Exercises",
                "type": "power",
                "description": "On a campus board, focus on big moves and deadpoints between rungs.",
                "priority": "high",
                "time_required": 45,
                "required_facilities": "campus_board"
            },
            {
                "name": "Campus Bouldering",
                "type": "power",
                "description": "Campus 3 boulder, 3 times with 2.5 minutes rest in between attempts",
                "priority": "medium",
                "time_required": 30,
                "required_facilities": "campus_board"
            },
            {
                "name": "Explosive Pull-Ups",
                "type": "power",
                "description": "From a dead hang, pull up explosively so that your hands briefly lose contact with the bar at the top. Control the descent.",
                "priority": "medium",
                "time_required": 15,
                "required_facilities": "fingerboard,pullup_bar"
            },

            # ————————————————
            # CORE
            # ————————————————
            {
                "name": "Front Lever Progressions",
                "type": "core",
                "description": "Work through progressions: tuck lever → advanced tuck → one-leg front lever → full front lever. Practice holding each position for 5-10 seconds.",
                "priority": "medium",
                "time_required": 10,
                "required_facilities": "fingerboard,pullup_bar"
            },
            {
                "name": "Hanging Knee Raises",
                "type": "core",
                "description": "3 sets of hanging knee raises",
                "priority": "medium",
                "time_required": 5,
                "required_facilities": "fingerboard,pullup_bar"
            },
            {
                "name": "Window Wipers",
                "type": "core",
                "description": "3 sets of window wipers",
                "priority": "medium",
                "time_required": 5,
                "required_facilities": "fingerboard,pullup_bar"
            },
            {
                "name": "Plank",
                "type": "core",
                "description": "3 sets of plank",
                "priority": "medium",
                "time_required": 10,
                "required_facilities": "fingerboard,pullup_bar"
            },
            {
                "name": "Hanging Leg Raises",
                "type": "core",
                "description": "3 sets of hanging leg raises",
                "priority": "medium",
                "time_required": 5,
                "required_facilities": "fingerboard,pullup_bar"
            },

            # ————————————————
            # TECHNIQUE DRILLS
            # ————————————————
            {
                "name": "Silent Feet Drills",
                "type": "technique",
                "description": "Climb a moderate route or problem, striving to place feet silently on each hold. Move slowly and focus on foot accuracy.",
                "priority": "high",
                "time_required": 10,
                "required_facilities": "bouldering_wall,lead_wall"
            },
            {
                "name": "Flagging Practice",
                "type": "technique", 
                "description": "On a slightly overhanging or vertical route, deliberately use flagging (placing one foot behind or across the other) to maintain balance.", 
                "priority": "medium", 
                "time_required": 10, 
                "required_facilities": "bouldering_wall,lead_wall"
            },
            {
                "name": "High-Step Drills",
                "type": "technique", 
                "description": "Climb a wall of moderate difficulty but force yourself to place your foot on a higher hold than usual.", 
                "priority": "medium", 
                "time_required": 10, 
                "required_facilities": "bouldering_wall"
            },
            {
                "name": "Cross-Through Drills",
                "type": "technique", 
                "description": "On a route with closely spaced holds, practice crossing one arm over the other to reach the next hold.", 
                "priority": "medium", 
                "time_required": 10, 
                "required_facilities": "bouldering_wall,lead_wall"
            },
            {
                "name": "Open-Hand Grip Practice",
                "type": "technique", 
                "description": "Climb routes or boulders using an open-hand grip (fingers slightly bent, not crimped).", 
                "priority": "medium", 
                "time_required": 10, 
                "required_facilities": "bouldering_wall,lead_wall,spray_wall,circuit_board,climbing_board"
            },
            {
                "name": "Slow Climbing",
                "type": "technique", 
                "description": "Pick a route and climb each move deliberately in slow motion. Pause on each hold.", 
                "priority": "high", 
                "time_required": 15, 
                "required_facilities": "bouldering_wall,lead_wall,spray_wall,circuit_board,climbing_board"
            }
        ]

        for ex_data in exercise_data:
            ex = Exercise(
                name=ex_data["name"],
                type=ex_data["type"],
                description=ex_data["description"],
                priority=ex_data.get("priority", "medium"),
                time_required=ex_data.get("time_required", 45),
                required_facilities=ex_data.get("required_facilities", "bouldering_wall")
            )
            db.add(ex)
            db.flush()  # ensure ex.id is available

            # If you ever add "best_for" in ex_data, insert ExerciseTarget rows
            if "best_for" in ex_data:
                for target in ex_data["best_for"]:
                    et = ExerciseTarget(exercise_id=ex.id, target=target)
                    db.add(et)

        db.commit()
        logger.info(f"Initialized {len(exercise_data)} exercises (plus any targets).")

    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing exercises: {e}")
        raise
    finally:
        db.close()


def init_badges():
    """Initialize badge categories and badges."""
    db = SessionLocal()
    try:
        # If at least one badge already exists, skip
        if db.query(Badge).count() > 0:
            logger.info("Badges already initialized, skipping.")
            return

        # 1) Create each badge category
        category_names = ["Climbing Styles", "Training Plans", "Projects", "Project Logs"]
        categories = {}
        for name in category_names:
            cat = BadgeCategory(name=name)
            db.add(cat)
            db.flush()
            categories[name] = cat.id

        # 2) Define badges under each category
        badges = [
            {
                "category": "Climbing Styles",
                "name": "Crimper",
                "description": "Master of small holds",
                "icon_name": "hand.raised",
                "how_to_earn": "Complete 5 crimpy routes"
            },
            {
                "category": "Climbing Styles",
                "name": "Sloper Master",
                "description": "Expert at friction climbing",
                "icon_name": "circle.fill",
                "how_to_earn": "Complete 5 sloper-heavy routes"
            },
            {
                "category": "Climbing Styles",
                "name": "Overhang Beast",
                "description": "Defies gravity on steep terrain",
                "icon_name": "arrow.up.right",
                "how_to_earn": "Complete 5 overhanging routes"
            },
            {
                "category": "Training Plans",
                "name": "Dedicated Planner",
                "description": "Created your first training plan",
                "icon_name": "calendar",
                "how_to_earn": "Generate a full training plan"
            },
            {
                "category": "Projects",
                "name": "Project Initiator",
                "description": "Started your first project",
                "icon_name": "flag.fill",
                "how_to_earn": "Create a new project"
            },
            {
                "category": "Project Logs",
                "name": "Consistent Logger",
                "description": "Logged 5 project entries",
                "icon_name": "pencil.tip",
                "how_to_earn": "Add five logs to a single project"
            }
        ]

        for bd in badges:
            badge = Badge(
                category_id=categories[bd["category"]],
                name=bd["name"],
                description=bd["description"],
                icon_name=bd["icon_name"],
                how_to_earn=bd["how_to_earn"]
            )
            db.add(badge)

        db.commit()
        logger.info(f"Initialized {len(badges)} badges across {len(category_names)} categories.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing badges: {e}")
        raise
    finally:
        db.close()


def main():
    """Entry point: initialize both exercises and badges."""
    logger.info("🔧 Starting database initialization...")
    init_exercises()
    init_badges()
    logger.info("✅ Database initialization complete!")


if __name__ == "__main__":
    main()

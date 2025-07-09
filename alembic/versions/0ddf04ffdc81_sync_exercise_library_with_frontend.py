"""sync exercise library with frontend

Revision ID: 0ddf04ffdc81
Revises: 272932d7ceed_convert_ids_to_uuid
Create Date: 2025-07-03 17:24:05.473714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ddf04ffdc81'
down_revision = '272932d7ceed_convert_ids_to_uuid'
branch_labels = None
depends_on = None

EXERCISES = [
    {
        "name": "Continuous Low-Intensity Climbing",
        "type": "aerobic_capacity",
        "description": (
            "Stay on the wall continuously for 20–40 minutes at a comfortably easy grade. "
            "Focus on smooth technique, controlled breathing and minimal rest on holds. "
            "Ideal for building your aerobic base and learning to recover under mild pump—"
            "great for endurance routes and recovery days."
        ),
        "priority": "high",
        "time_required": 30,
        "required_facilities": "circuit_board,lead_wall,auto_belay",
    },
    {
        "name": "Mixed Intensity Laps",
        "type": "aerobic_capacity",
        "description": (
            "Alternate between an easy circuit and one at your onsight level for 30–40 moves total. "
            "Rest 8–12 minutes between reps. Builds your ability to switch effort on the fly—"
            "ideal for long sport routes or trad where pace changes frequently."
        ),
        "priority": "medium",
        "time_required": 45,
        "required_facilities": "circuit_board,lead_wall",
    },
    {
        "name": "X-On, X-Off Intervals",
        "type": "aerobic_capacity",
        "description": (
            "Climb for 10 minutes at moderate intensity, then rest 10 minutes. "
            "Repeat 3–4 times. Trains your ability to clear lactate under load—"
            "great for sustained routes with few rests."
        ),
        "priority": "high",
        "time_required": 60,
        "required_facilities": "circuit_board,lead_wall",
    },
    {
        "name": "Route 4x4s",
        "type": "aerobic_capacity",
        "description": (
            "Lead the same route 4 times back-to-back with minimal rest—"
            "just enough to re-tie or chalk. Builds sustained endurance and mental toughness."
        ),
        "priority": "high",
        "time_required": 60,
        "required_facilities": "circuit_board,lead_wall",
    },
    {
        "name": "Linked Laps",
        "type": "aerobic_capacity",
        "description": (
            "Climb a moderate route, lower off, shake out for 60 s, then climb again—"
            "2–3 laps per set. Teaches pacing and recovery under pump."
        ),
        "priority": "medium",
        "time_required": 30,
        "required_facilities": "circuit_board,lead_wall",
    },
    {
        "name": "Low Intensity Fingerboarding",
        "type": "aerobic_capacity",
        "description": (
            "Using 30–40 % of your max hang, perform 7 s hang / 3 s rest for 10–16 reps. "
            "Repeat 6–10 sets with 1 min rest. Builds forearm endurance."
        ),
        "priority": "medium",
        "time_required": 30,
        "required_facilities": "fingerboard",
    },
    {
        "name": "Foot-On Campus Endurance",
        "type": "aerobic_capacity",
        "description": (
            "Keep feet on campus rungs or small footholds—move continuously for 5–10 min. "
            "Short rests only. Builds forearm endurance & core tension."
        ),
        "priority": "medium",
        "time_required": 30,
        "required_facilities": "campus_board",
    },

    # ————————————————
    # ANEROBIC CAPACITY
    # ————————————————
    {
        "name": "Long Boulder Circuits",
        "type": "anaerobic_capacity",
        "description": (
            "Link 12–15 moves on a boulder or board. Rest 2–4× the climb time. "
            "Repeat 8–10 reps. Trains power-endurance in sustained sequences."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "bouldering_wall,circuit_board",
    },
    {
        "name": "Boulder Triples",
        "type": "anaerobic_capacity",
        "description": (
            "Pick three 6–8-move problems at flash level. Climb each three times "
            "with 60 s rest between climbs and 3 min between problems. Builds repeat power."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "bouldering_wall,circuit_board",
    },
    {
        "name": "Linked Bouldering Circuits",
        "type": "anaerobic_capacity",
        "description": (
            "String together 2–3 boulder problems without touching the ground. "
            "Rest 4–5 min between sets. Simulates back-to-back cruxes."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "bouldering_wall,circuit_board",
    },
    {
        "name": "Campus Laddering",
        "type": "anaerobic_capacity",
        "description": (
            "Hand-over-hand up/down the campus board for 15–20 moves, rest 2–3 min. "
            "8–10 sets. Boosts lactic tolerance on steep terrain."
        ),
        "priority": "medium",
        "time_required": 30,
        "required_facilities": "campus_board",
    },
    {
        "name": "Fingerboard Repeater Blocks",
        "type": "anaerobic_capacity",
        "description": (
            "4 × (7 s hang / 3 s rest) = one block. Rest 2–3 min. 3–5 blocks. "
            "Builds finger pump tolerance under load."
        ),
        "priority": "medium",
        "time_required": 30,
        "required_facilities": "fingerboard",
    },
    {
        "name": "Multiple Set Boulder Circuits",
        "type": "anaerobic_capacity",
        "description": (
            "Design a 3-problem linked circuit. Climb 4–5×, rest 10–20 min, repeat 2–3×. "
            "Great for redpoint power-endurance."
        ),
        "priority": "high",
        "time_required": 60,
        "required_facilities": "bouldering_wall,circuit_board",
    },
    {
        "name": "Density Hangs",
        "type": "anaerobic_capacity",
        "description": (
            "Hang for 20–40 s at moderate load on fingerboard or jugs, rest equally. "
            "6–8 cycles. Builds forearm pump tolerance."
        ),
        "priority": "medium",
        "time_required": 20,
        "required_facilities": "fingerboard",
    },

    # ————————————————
    # AEROBIC POWER
    # ————————————————
    {
        "name": "30-Move Circuits",
        "type": "aerobic_power",
        "description": (
            "Link 30 moves on a board or wall without shaking out. Rest 1–2× climb time. "
            "4–5 reps. Builds sustained power between easy and hard efforts."
        ),
        "priority": "high",
        "time_required": 30,
        "required_facilities": "circuit_board,bouldering_wall",
    },
    {
        "name": "On-The-Minute Bouldering",
        "type": "aerobic_power",
        "description": (
            "EMOM: 1 attempt of a 6–8-move problem every minute for 8 min. "
            "Short rests force rapid recovery."
        ),
        "priority": "high",
        "time_required": 30,
        "required_facilities": "circuit_board,bouldering_wall",
    },
    {
        "name": "Boulder 4x4s",
        "type": "aerobic_power",
        "description": (
            "Choose 4 problems at or just below limit. Climb back-to-back, rest 1–3 min, "
            "repeat 4× total. Builds power-endurance."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "bouldering_wall,circuit_board",
    },
    {
        "name": "3x3 Bouldering Circuits",
        "type": "aerobic_power",
        "description": (
            "Pick 3 boulders. Climb each 3× with minimal rest, then rest longer between sets. "
            "2–3 full circuits. Great for repeated crux power."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "bouldering_wall,circuit_board",
    },
    {
        "name": "Intensive Foot-On Campus",
        "type": "aerobic_power",
        "description": (
            "Feet on low footholds—campus up/down for 1 min, rest 1–2 min, 8 reps. "
            "Targets forearm pump on steep terrain."
        ),
        "priority": "high",
        "time_required": 20,
        "required_facilities": "campus_board",
    },

    # ————————————————
    # ANAEROBIC POWER
    # ————————————————
    {
        "name": "Short Boulder Repeats",
        "type": "anaerobic_power",
        "description": (
            "5–7 moves near max. Climb ×4 with 1:1 rest, 10 min between sets, 4 sets. "
            "Builds absolute crux power."
        ),
        "priority": "high",
        "time_required": 60,
        "required_facilities": "bouldering_wall,circuit_board",
    },
    {
        "name": "Broken Circuits",
        "type": "anaerobic_power",
        "description": (
            "25-move circuit broken into 3–4 chunks. Climb chunks with minimal rest, "
            "then link fully over time. Trains linking hard sections."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "circuit_board,bouldering_wall",
    },
    {
        "name": "Max Intensity Redpoints",
        "type": "anaerobic_power",
        "description": (
            "Project a 20–30 move route at your limit. 10+ min rest between redpoint attempts. "
            "Builds max power and mental resilience."
        ),
        "priority": "medium",
        "time_required": 60,
        "required_facilities": "lead_wall,bouldering_wall",
    },

    # ————————————————
    # STRENGTH
    # ————————————————
    {
        "name": "Max Boulder Sessions",
        "type": "strength",
        "description": (
            "Work 2–3 problems at your absolute limit with 3–5 min full rest. "
            "Emphasize perfect technique on each max effort."
        ),
        "priority": "high",
        "time_required": 60,
        "required_facilities": "bouldering_wall",
    },
    {
        "name": "Board Session",
        "type": "strength",
        "description": (
            "Use a Moon or Kilter board: 10 problems pyramid from easy→max→easy, "
            "3–5 min rest. Targets specific move strength."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "climbing_board",
    },
    {
        "name": "Boulder Pyramids",
        "type": "strength",
        "description": (
            "2@easy, 2@mid, 2@max, then back down. 3–4 min rest. "
            "Combines power & strength-endurance under fatigue."
        ),
        "priority": "high",
        "time_required": 60,
        "required_facilities": "bouldering_wall",
    },
    {
        "name": "Boulder Intervals",
        "type": "strength",
        "description": (
            "5 problems at –2–3 grades. Climb each 3× with 3 min rest between reps. "
            "15 total attempts builds power-endurance."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "bouldering_wall",
    },
    {
        "name": "Volume Bouldering",
        "type": "strength",
        "description": (
            "15 moderate problems in 45 min. Pace to maintain form while accruing pump. "
            "Builds work capacity."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "bouldering_wall",
    },
    {
        "name": "Fingerboard Max Hangs (Crimps)",
        "type": "strength",
        "description": (
            "10 s hangs on 15–20 mm crimps with added weight near max. 2–3 min rest, 5–8 hangs. "
            "Builds maximal finger strength."
        ),
        "priority": "high",
        "time_required": 30,
        "required_facilities": "fingerboard",
    },
    {
        "name": "Fingerboard Max Hangs (Pockets)",
        "type": "strength",
        "description": (
            "10 s hangs on 2- or 3-finger pockets near max. 2–3 min rest, 5–8 hangs. "
            "Targets pocket strength."
        ),
        "priority": "high",
        "time_required": 30,
        "required_facilities": "fingerboard",
    },
    {
        "name": "Dead Hangs",
        "type": "strength",
        "description": (
            "Hang on edges/jugs for 20–30 s, rest 90 s, 5 sets. "
            "Fundamental grip & shoulder stability."
        ),
        "priority": "medium",
        "time_required": 15,
        "required_facilities": "fingerboard,pullup_bar",
    },
    {
        "name": "Weighted Pull-Ups",
        "type": "strength",
        "description": (
            "Add weight to pull-ups, 3–8 reps per set, 2–3 min rest. "
            "Builds back & arm pulling strength."
        ),
        "priority": "medium",
        "time_required": 20,
        "required_facilities": "pullup_bar",
    },
    {
        "name": "One-Arm Lock-Offs",
        "type": "strength",
        "description": (
            "Pull up with both arms, remove one and hold lock-off 5–7 s. "
            "3–4 sets each arm. Builds unilateral pulling control."
        ),
        "priority": "medium",
        "time_required": 20,
        "required_facilities": "pullup_bar",
    },

    # ————————————————
    # POWER
    # ————————————————
    {
        "name": "Campus Board Exercises",
        "type": "power",
        "description": (
            "Big moves & deadpoints on a campus board. <20 min, 2–3 min rest between max efforts. "
            "Boosts explosive pulling."
        ),
        "priority": "high",
        "time_required": 45,
        "required_facilities": "campus_board",
    },
    {
        "name": "Campus Bouldering",
        "type": "power",
        "description": (
            "Campus three positive‐hold boulders 3× each with 2.5 min rest. "
            "Develops contact strength & explosive power."
        ),
        "priority": "medium",
        "time_required": 30,
        "required_facilities": "campus_board",
    },
    {
        "name": "Explosive Pull-Ups",
        "type": "power",
        "description": (
            "From dead hang, pull so hands briefly lose bar contact. 3–5 reps, full rest. "
            "Builds dyno power."
        ),
        "priority": "medium",
        "time_required": 15,
        "required_facilities": "pullup_bar",
    },

    # ————————————————
    # CORE
    # ————————————————
    {
        "name": "Front Lever Progressions",
        "type": "core",
        "description": (
            "Progress from tuck → advanced tuck → one-leg → full front lever. "
            "Hold 5–10 s, 4–5 sets. Builds core & shoulder tension."
        ),
        "priority": "high",
        "time_required": 15,
        "required_facilities": "pullup_bar",
    },
    {
        "name": "Hanging Knee Raises",
        "type": "core",
        "description": (
            "Hang, then raise knees to chest. 3 × 10–15 reps. "
            "Targets lower abs & hip flexors."
        ),
        "priority": "medium",
        "time_required": 5,
        "required_facilities": "pullup_bar",
    },
    {
        "name": "Window Wipers",
        "type": "core",
        "description": (
            "Hang, legs at 90°, rotate side-to-side. 3 × 8–10 reps. "
            "Builds obliques & rotational control."
        ),
        "priority": "medium",
        "time_required": 5,
        "required_facilities": "pullup_bar",
    },
    {
        "name": "Plank",
        "type": "core",
        "description": (
            "Forearm plank, hold 30–60 s, 3 sets. "
            "Foundational core stability."
        ),
        "priority": "medium",
        "time_required": 10,
        "required_facilities": "mat",
    },
    {
        "name": "Hanging Leg Raises",
        "type": "core",
        "description": (
            "Hang, legs straight, raise to 90°. 3 × 8–12 reps. "
            "Deep core & hip flexor strength."
        ),
        "priority": "medium",
        "time_required": 5,
        "required_facilities": "pullup_bar",
    },

    # ————————————————
    # MOBILITY
    # ————————————————
    {
        "name": "Flexibility and Mobility Circuit",
        "type": "mobility",
        "description": (
            "15 min circuit targeting hips, shoulders, ankles. Static holds (30–60 s) + dynamic movements. "
            "Improves range for high steps & stems."
        ),
        "priority": "high",
        "time_required": 15,
        "required_facilities": "mat,foam_block,band",
    },
    {
        "name": "Dynamic Hip Mobility",
        "type": "mobility",
        "description": (
            "Leg swings, hip circles, world’s greatest stretch. 10–12 min before climbing. "
            "Preps hips for technical footwork."
        ),
        "priority": "medium",
        "time_required": 12,
        "required_facilities": "mat",
    },
    {
        "name": "Shoulder Mobility Flow",
        "type": "mobility",
        "description": (
            "Arm circles, wall slides, band pull-aparts, dislocates. 8–10 min. "
            "Improves overhead reach & lock-off health."
        ),
        "priority": "medium",
        "time_required": 10,
        "required_facilities": "band,wall",
    },
    {
        "name": "Ankle and Foot Mobility",
        "type": "mobility",
        "description": (
            "Calf stretches, ankle circles, towel scrunches, balance work. "
            "Enhances edging & smearing precision."
        ),
        "priority": "medium",
        "time_required": 10,
        "required_facilities": "step,balance_board,towel",
    },

    # ————————————————
    # WARM UP & COOL DOWN
    # ————————————————
    {
        "name": "General Warm-up",
        "type": "warm_up",
        "description": (
            "5 min light cardio + dynamic stretches + easy traversing up to 80 % intensity. "
            "Prepares body for climbing."
        ),
        "priority": "high",
        "time_required": 15,
        "required_facilities": "wall,open_space",
    },
    {
        "name": "Dynamic Stretching",
        "type": "warm_up",
        "description": (
            "Arm circles, leg swings, lunges, torso twists. 5–10 min. "
            "Improves ROM and primes muscles."
        ),
        "priority": "medium",
        "time_required": 10,
        "required_facilities": "open_space",
    },
    {
        "name": "Light Stretching",
        "type": "cool_down",
        "description": (
            "Static forearm, shoulder, hip, hamstring, calf stretches. 10–15 min. "
            "Promotes recovery and flexibility."
        ),
        "priority": "medium",
        "time_required": 15,
        "required_facilities": "mat",
    },
    {
        "name": "Cool-down Exercises",
        "type": "cool_down",
        "description": (
            "5–10 min easy traversing + 5 min walking + antagonist work + deep breathing. "
            "Aids waste removal and relaxation."
        ),
        "priority": "medium",
        "time_required": 20,
        "required_facilities": "wall,mat",
    },

    # ————————————————
    # TECHNIQUE
    # ————————————————
    {
        "name": "Silent Feet Drills",
        "type": "technique",
        "description": (
            "Climb silently on moderate terrain—no foot noise. "
            "Teaches precise footwork and control."
        ),
        "priority": "high",
        "time_required": 10,
        "required_facilities": "wall",
    },
    {
        "name": "Flagging Practice",
        "type": "technique",
        "description": (
            "Use inside, outside & rear flags on overhangs to counter barn-doors. "
            "Improves balance & body positioning."
        ),
        "priority": "medium",
        "time_required": 10,
        "required_facilities": "wall",
    },
    {
        "name": "High-Step Drills",
        "type": "technique",
        "description": (
            "Deliberately place foot above waist level on holds. "
            "Builds hip flexibility & pull-up strength."
        ),
        "priority": "medium",
        "time_required": 10,
        "required_facilities": "wall",
    },
    {
        "name": "Cross-Through Drills",
        "type": "technique",
        "description": (
            "Traverse using cross-through reaches. "
            "Enhances fluid movement & reach coordination."
        ),
        "priority": "medium",
        "time_required": 10,
        "required_facilities": "wall",
    },
    {
        "name": "Open-Hand Grip Practice",
        "type": "technique",
        "description": (
            "Climb using open-hand on edges & slopers. "
            "Builds sloper strength & reduces crimp injury risk."
        ),
        "priority": "medium",
        "time_required": 15,
        "required_facilities": "wall",
    },
    {
        "name": "Slow Climbing",
        "type": "technique",
        "description": (
            "Climb at ⅓ normal speed, pausing 3–5 s on each hold. "
            "Trains precision, planning & composure."
        ),
        "priority": "high",
        "time_required": 15,
        "required_facilities": "wall",
    },
    {
        "name": "Rest Position Training",
        "type": "technique",
        "description": (
            "Identify and optimize shakes, knee bars & stems. "
            "Practice conscious breathing and weight shifts."
        ),
        "priority": "medium",
        "time_required": 10,
        "required_facilities": "wall",
    },
    {
        "name": "Dynamic Movement Practice",
        "type": "technique",
        "description": (
            "Progress from deadpoints to full dynos. "
            "Focus on setup, momentum & catch mechanics."
        ),
        "priority": "medium",
        "time_required": 15,
        "required_facilities": "bouldering_area",
    },
]

def upgrade():
    op.create_index("ux_exercises_name", "exercises", ["name"], unique=True)

    conn = op.get_bind()

    # --- 2) DELETE any DB rows not in the UI list ---
    names = [ex["name"] for ex in EXERCISES]
    conn.execute(
        sa.text("DELETE FROM exercises WHERE name NOT IN :names"),
        {"names": tuple(names)}
    )

    # --- 3) UPSERT each UI exercise ---
    # This uses Postgres ON CONFLICT on the unique name.
    for ex in EXERCISES:
        conn.execute(
            sa.text("""
                INSERT INTO exercises
                  (name, type, description, priority, time_required, required_facilities)
                VALUES
                  (:name, :type, :description, :priority, :time_required, :required_facilities)
                ON CONFLICT (name)
                DO UPDATE SET
                  type               = EXCLUDED.type,
                  description        = EXCLUDED.description,
                  priority           = EXCLUDED.priority,
                  time_required      = EXCLUDED.time_required,
                  required_facilities= EXCLUDED.required_facilities
            """),
            ex
        )


def downgrade() -> None:
    op.drop_index("ux_exercises_name", table_name="exercises")

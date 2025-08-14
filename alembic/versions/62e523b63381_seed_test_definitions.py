"""seed test_definitions

Revision ID: 62e523b63381
Revises: 5366d3563e34
Create Date: 2025-08-13 20:19:56.592561
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "62e523b63381"
down_revision: Union[str, None] = "5366d3563e34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---- Data to seed ----
TESTS = [
    {
        "name": "Finger Strength – Half Crimp",
        "unit": "kg",
        "description": (
            "Measures max two-arm finger force in a strict half-crimp. Use a fixed edge and "
            "increase load in small steps. Each attempt is a 7-second hang with 2-minute rest. "
            "Record the heaviest successful 7-second hang as TOTAL LOAD (bodyweight ± added/assisted). "
            "%BW = total/bodyweight × 100. Standardize elbow angle (150–180°), grip (no thumb wrap) "
            "and edge depth. Stop on form break or pain."
        ),
    },
    {
        "name": "Open Grip – Four Fingers",
        "unit": "kg",
        "description": (
            "Max two-arm strength in open hand with all four fingertips. Same 7-second protocol and "
            "2-minute rests. Record TOTAL LOAD (kg) and optionally %BW. Keep hand open (don’t drift into crimp) "
            "and elbow angle consistent."
        ),
    },
    {
        "name": "Front-3 Open Drag",
        "unit": "kg",
        "description": (
            "Max two-arm strength using index–middle–ring in open drag. Same 7-second protocol; use smaller "
            "load steps (1–2 kg). Record TOTAL LOAD (kg). Abort if any finger loses contact."
        ),
    },
    {
        "name": "One-Arm Finger Strength",
        "unit": "kg",
        "description": (
            "One-arm max hang for 10 seconds in half-crimp or open hand with assistance pulley if needed. "
            "Maintain shoulder engagement and elbow 90–180°. Increase/decrease assistance in 1–2 kg steps with "
            "2–3 minute rests. Record BEST ARM TOTAL LOAD (kg) and put L/R values in notes."
        ),
    },
    {
        "name": "Lactate Curve (7:3)",
        "unit": "s",
        "description": (
                "Alternate 7 s hangs with 3 s rest to failure for a max bout; record total time (s). Then complete 7 "
                "additional 7:3 sets to failure, resting the same time you just achieved. Put the seven follow-up set "
                "times in notes (comma-separated). Keep edge, grip and elbow angle consistent."
        ),
    },
    {
        "name": "Max Moves – Foot-On Campus",
        "unit": "s",
        "description": (
            "With feet supported, repeat a steady 1–2–3–2–1 hand sequence to failure. Record total time (s). "
            "Standardize rung sizes, foot support and tempo. Stop if form breaks."
        ),
    },
    {
        "name": "Power Endurance – 75% (7:3)",
        "unit": "s",
        "description": (
            "Use 75% of your two-arm max-hang TOTAL load. Perform 7 s on / 3 s off to failure; record total time (s). "
            "Put the load adjustment (assist or add) in notes. Keep edge, grip and elbow angle identical to the max "
            "test used to compute the load."
        ),
    },
    {
        "name": "Weighted Pull-Up – 2RM",
        "unit": "kg",
        "description": (
            "Find the heaviest load for two strict pull-ups. Increase in 2.5–5 kg steps with 3 minute rests. "
            "Record added weight (kg); use negative for assistance if applicable."
        ),
    },
]

def upgrade() -> None:
    conn = op.get_bind()
    insert_sql = sa.text("""
        INSERT INTO test_definitions (name, description, unit, exercise_id)
        VALUES (:name, :description, :unit, NULL)
        ON CONFLICT (name) DO NOTHING
    """)
    # executemany: pass a list of dicts
    conn.execute(insert_sql, TESTS)

def downgrade() -> None:
    conn = op.get_bind()
    delete_sql = sa.text("DELETE FROM test_definitions WHERE name = :name")
    # executemany delete
    conn.execute(delete_sql, [{"name": t["name"]} for t in TESTS])

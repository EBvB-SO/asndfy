import pytest
from app.services.plan_generator import PlanGeneratorService
from app.models.training_plan import PhasePlanRequest, FullPlanRequest

@pytest.fixture
def svc():
    return PlanGeneratorService()

def make_req(
    angles="overhanging",
    lengths="long, short",
    holds="crimpy, slopers, pockets, pinches",
    desc="Sustained pumpy sections with a dyno crux.",
    strengths="power,endurance",
    weaknesses="technique",
    facilities="rope,bouldering_wall,fingerboard,campus",
    injuries="none",
    time="2 hours",
    experience="3 years",
    attr_ratings="power:4,endurance:3,technique:2",
    notes="Prefers morning sessions",
    weeks_to_train="6",
    sessions_per_week="4",
    general_fitness="average",
    height="1.8",
    weight="70.0",
    age="24",
    preferred_climbing_style="sport",
    indoor_vs_outdoor="indoor",
    onsight_flash_level="5+",
    redpointing_experience="intermediate",
    sleep_recovery="good",
    work_life_balance="balanced",
    fear_factors="none",
    mindfulness_practices="none",
    motivation_level="high",
    access_to_coaches="no",
    time_for_cross_training="none",
):
    return PhasePlanRequest(
        route="The Cider Soak",
        grade="8a",
        crag="Anstey's Cove",
        route_angles=angles,
        route_lengths=lengths,
        hold_types=holds,
        route_description=desc,
        current_climbing_grade="7c",
        max_boulder_grade="V6",
        perceived_strengths=strengths,
        perceived_weaknesses=weaknesses,
        training_facilities=facilities,
        injury_history=injuries,
        time_per_session=time,
        training_experience=experience,
        attribute_ratings=attr_ratings,
        additional_notes=notes,
        weeks_to_train=weeks_to_train,
        sessions_per_week=sessions_per_week,
        general_fitness=general_fitness,
        height=height,
        weight=weight,
        age=age,
        preferred_climbing_style=preferred_climbing_style,
        indoor_vs_outdoor=indoor_vs_outdoor,
        onsight_flash_level=onsight_flash_level,
        redpointing_experience=redpointing_experience,
        sleep_recovery=sleep_recovery,
        work_life_balance=work_life_balance,
        fear_factors=fear_factors,
        mindfulness_practices=mindfulness_practices,
        motivation_level=motivation_level,
        access_to_coaches=access_to_coaches,
        time_for_cross_training=time_for_cross_training,
    )

def test_full_analyze_route(svc):
    f = svc.analyze_route("Test Route", "8a", "Test Crag", make_req())
    # flags
    assert f["is_steep"] is True
    assert f["is_technical"] is True
    assert f["is_endurance"] is True
    assert f["is_power"] is True
    assert f["is_crimpy"] is True
    assert f["is_slopey"] is True
    assert f["is_pockety"] is True

    # key challenges includes all mapped keywords
    for challenge in (
        "steepness",
        "technical movement",
        "endurance",
        "power",
        "small holds",
        "slopers",
        "pockets",
        "pinches"
    ):
        assert challenge in f["key_challenges"]

    # primary_style: since both steep & power are True
    assert f["primary_style"] == "powerful overhanging"

def make_full_req(**kwargs):
    """
    Wrap the PhasePlanRequest in a FullPlanRequest, supplying weeks and sessions.
    """
    phase_req = make_req(**kwargs)
    return FullPlanRequest(
        plan_data=phase_req,
        weeks_to_train=8,           # e.g. 8‐week plan
        sessions_per_week=4,        # e.g. 4 sessions per week
        previous_analysis=None
    )

def test_full_plan_round_trip(svc):
    full_req = make_full_req()
    plan = svc.generate_full_plan(full_req)

    # It should produce exactly 8 weeks worth split into phases,
    # with at most 4 sessions in each weekly_schedule,
    # and every "focus" must match one of your DB exercises...
    assert "phases" in plan
    assert isinstance(plan["phases"], list)

def test_steep_and_technical_from_angles(svc):
    f = svc.analyze_route("X","7a+","Y", make_req(angles="overhanging, slab"))
    assert f["is_steep"] is True
    assert f["is_technical"] is True
    assert "steepness" in f["key_challenges"]
    assert "technical movement" in f["key_challenges"]

def test_endurance_and_power_from_lengths(svc):
    f = svc.analyze_route("X","7a+","Y", make_req(lengths="long, short"))
    assert f["is_endurance"] is True
    assert f["is_power"] is True
    assert set(["endurance","power"]).issubset(f["key_challenges"])

def test_hold_types_all_flags(svc):
    f = svc.analyze_route("X","7a+","Y", make_req(holds="crimpy, slopers, pockets, pinches"))
    assert f["is_crimpy"] is True
    assert f["is_slopey"] is True
    assert f["is_pockety"] is True
    assert "pinches" in f["key_challenges"]

def test_description_keyword_mapping(svc):
    desc = "Sustained climbing with a dyno crux, delicate balance, and slopers."
    f = svc.analyze_route("X","7a+","Y", make_req(desc=desc))
    assert f["is_endurance"] is True   # “sustained”
    assert f["is_power"] is True       # “dyno”
    assert f["is_technical"] is True   # “delicate”, “balance”
    assert f["is_slopey"] is True      # “slopers”
    for ch in ("endurance","power","technical movement","slopers"):
        assert ch in f["key_challenges"]

def test_primary_style_priority(svc):
    # steep + power → powerful overhanging
    f = svc.analyze_route("X","7a+","Y", make_req(angles="roof", lengths="short"))
    assert f["primary_style"] == "powerful overhanging"
    # slab only → technical face
    f2 = svc.analyze_route("X","7a+","Y", make_req(angles="slab"))
    assert f2["primary_style"] == "technical face"

def test_no_inputs_means_all_false(svc):
    # if the climber gives no route characteristics, no flags light up
    f = svc.analyze_route(
        "X","7a+","Y",
        make_req(angles="", lengths="", holds="", desc="")
    )
    assert all(not f[flag] for flag in (
        "is_steep","is_technical","is_endurance","is_power",
        "is_crimpy","is_slopey","is_pockety"
    ))
    assert f["key_challenges"] == []

def test_only_description_endurance(svc):
    # even without lengths, "endurance" in desc flips is_endurance
    desc = "super sustained moves, big pump at top"
    f = svc.analyze_route(
        "X","7a+","Y",
        make_req(angles="", lengths="", holds="", desc=desc)
    )
    assert f["is_endurance"] is True
    assert "endurance" in f["key_challenges"]
    # but nothing else
    assert f["is_power"] is False

def test_mixed_case_and_extra_spaces(svc):
    # ensure keyword matching is case-insensitive and strips spaces
    desc = "  DynO   ,  sLoPeRs "
    f = svc.analyze_route(
        "X","7a+","Y",
        make_req(angles="", lengths="", holds="", desc=desc)
    )
    assert f["is_power"] is True
    assert f["is_slopey"] is True
    assert set(f["key_challenges"]) == {"power","slopers"}
# services/description_keywords.py

# Map free-form description keywords to feature flags + challenge labels
DESCRIPTION_KEYWORDS = {
    "is_endurance": {
        "keywords": [
            "sustained", "stamina", "endurance", "pump",
            "all-day", "continuous", "long sequences"],
        "challenge": "endurance"
    },

    "is_power": {
        "keywords": [
            "powerful", "dynamic", "dyno", "explosive",
            "bouldery", "hard move", "max effort"],
        "challenge": "power"
    },
    
    "is_technical": {
        "keywords": [
            "technical", "precise", "balance", "delicate",
            "crux", "sequenced moves", "footwork", "slab"],
        "challenge": "technical movement"
    },

    "is_crimpy": {
        "keywords": ["crimp", "edge", "small holds", "tiny crimps"],
        "challenge": "small holds"
    },

    "is_slopey": {
        "keywords": ["sloper", "round hold", "sloppy", "friction"],
        "challenge": "slopers"
    },

    "is_pockety": {
        "keywords": [
            "pocket", "deep pocket", "mono pocket", "frankenjura",
            "duo pocket", "hole"],
        "challenge": "pockets"
    },

    "is_steep": {
        "keywords": ["overhang", "roof", "roofy", "steep"],
        "challenge": "steepness"
    }
}

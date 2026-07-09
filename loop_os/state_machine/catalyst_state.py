ALLOWED_TRANSITIONS = {
    "discovered": {"validating", "rejected"},
    "validating": {"confirmed", "expired", "rejected"},
    "confirmed": {"priced_in", "expired"},
    "priced_in": {"expired"},
    "expired": set(),
    "rejected": set(),
}


def can_transition(source: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(source, set())

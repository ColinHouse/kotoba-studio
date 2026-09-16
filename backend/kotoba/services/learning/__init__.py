"""学习域：词条、语境、卡片。The learner's own vocabulary, built from what they met."""

from kotoba.services.learning.cards import CARD_TYPES, card_to_dict, create_cards, default_owner
from kotoba.services.learning.queries import (
    encounter_timeline,
    search_terms,
    term_detail,
    term_summary,
)
from kotoba.services.learning.terms import (
    add_encounter,
    bulk_set_status,
    ensure_sense,
    get_or_create_term,
)
from kotoba.services.learning.traps import homograph_trap

__all__ = [
    "CARD_TYPES",
    "add_encounter",
    "bulk_set_status",
    "card_to_dict",
    "create_cards",
    "default_owner",
    "encounter_timeline",
    "ensure_sense",
    "get_or_create_term",
    "homograph_trap",
    "search_terms",
    "term_detail",
    "term_summary",
]

from agents.encounter_research.matcher import match_actions_for_ability
from agents.encounter_research.models import ExtractedAction
from agents.encounter_research.reconciler import reconcile_match_results


def make_action(
    name: str,
    description: str,
    classification: str,
    site: str = "icy-veins",
    *,
    is_dot: bool = False,
    is_multi_hit: bool = False,
):
    return ExtractedAction(
        site=site,
        url=f"https://example.com/{name}",
        title="Guide",
        phase="Phase 1",
        action_name=name,
        description=description,
        classification=classification,
        is_dot=is_dot,
        is_multi_hit=is_multi_hit,
        damage_link_likelihood=0.95,
        evidence_quote=description,
    )


def test_matcher_prefers_exact_name_matches():
    actions = [
        make_action("Crown of Arcadia", "Raidwide", "raidwide"),
        make_action("Raw Steel", "Tankbuster", "dual_tankbuster", is_multi_hit=True),
    ]

    matches = match_actions_for_ability("Crown of Arcadia", actions)

    assert matches[0].action.action_name == "Crown of Arcadia"
    assert matches[0].score == 1.0


def test_matcher_returns_fuzzy_match_for_similar_names():
    actions = [
        make_action("Crown Arcadia", "Raidwide", "raidwide"),
    ]

    matches = match_actions_for_ability("Crown of Arcadia", actions)

    assert len(matches) == 1
    assert matches[0].strategy == "fuzzy"


def test_reconciler_flags_conflicting_guides_as_disputed():
    matches = [
        match_actions_for_ability(
            "Crown of Arcadia",
            [
                make_action("Crown of Arcadia", "Raidwide hit", "raidwide", site="icy-veins"),
                make_action("Crown of Arcadia", "Small-party hit", "small_party", site="hardcore-gamer"),
            ],
        )[0],
        match_actions_for_ability(
            "Crown of Arcadia",
            [
                make_action("Crown of Arcadia", "Raidwide hit", "raidwide", site="icy-veins"),
                make_action("Crown of Arcadia", "Small-party hit", "small_party", site="hardcore-gamer"),
            ],
        )[1],
    ]

    annotation = reconcile_match_results(
        "Crown of Arcadia",
        matches,
        heuristic_label="raidwide",
        llm_client=None,
    )

    assert annotation.status == "disputed"
    assert len(annotation.sources) == 2


def test_reconciler_uses_heuristic_fallback_for_unmatched_ability():
    annotation = reconcile_match_results(
        "Unknown Ability",
        [],
        heuristic_label="dual_tankbuster:multi_hit",
        llm_client=None,
    )

    assert annotation.status == "unmatched"
    assert annotation.classification == "dual_tankbuster"
    assert annotation.is_multi_hit is True

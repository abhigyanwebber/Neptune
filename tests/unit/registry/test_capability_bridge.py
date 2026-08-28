"""Unit tests for the capability vocabulary bridge (C-006).

Verifies mapping coverage, canonical passthrough, unknown/rejected
handling, deduplication, and determinism -- all against the actual
current vocabularies (core.registry.capability_registry.KNOWN_CAPABILITIES
and the values in neptune.core.domain.capability.Capability, transcribed
here as plain strings -- this file intentionally does NOT import that
enum, mirroring the bridge module's own constraint of never importing
anything from src/neptune)."""
import pytest

from core.registry.capability_bridge import (
    EXTERNAL_TO_CANONICAL,
    REJECTED_EXTERNAL_CAPABILITIES,
    RejectedExternalCapabilityError,
    UnknownExternalCapabilityError,
    translate_capabilities,
    translate_capability,
)
from core.registry.capability_registry import KNOWN_CAPABILITIES

# Transcribed directly from src/neptune/core/domain/capability.py's
# Capability enum values, as of this task's inspection (C-006 requirement:
# "verify in the actual repository", not assume from earlier reports).
LEGACY_B_SIDE_CAPABILITY_VALUES = {
    "fast_general",
    "coding",
    "reasoning",
    "planning",
    "summarization",
    "classification",
    "tool_use",
    "vision",
    "embedding",
    "frontier_escalation",
}


# ---------------------------------------------------------------------------
# Every valid mapping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "external_id",
    ["coding", "reasoning", "planning", "summarization", "classification", "tool_use", "vision", "embedding"],
)
def test_every_overlapping_legacy_value_translates_to_itself(external_id):
    assert translate_capability(external_id) == external_id


def test_mapping_table_covers_exactly_the_overlapping_legacy_values():
    overlap = LEGACY_B_SIDE_CAPABILITY_VALUES & KNOWN_CAPABILITIES
    assert set(EXTERNAL_TO_CANONICAL.keys()) == overlap


def test_every_mapping_table_value_is_a_canonical_capability():
    for canonical_id in EXTERNAL_TO_CANONICAL.values():
        assert canonical_id in KNOWN_CAPABILITIES


# ---------------------------------------------------------------------------
# Canonical passthrough
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("canonical_only_id", ["web_search", "mcp", "browser", "terminal", "memory"])
def test_canonical_only_capabilities_pass_through_unchanged(canonical_only_id):
    # These have no legacy/B-side representation at all -- the bridge
    # must still translate them (identity) since it's idempotent for
    # anything already canonical.
    assert canonical_only_id not in LEGACY_B_SIDE_CAPABILITY_VALUES
    assert translate_capability(canonical_only_id) == canonical_only_id


def test_passthrough_covers_every_canonical_capability_not_in_the_mapping_table():
    for canonical_id in KNOWN_CAPABILITIES:
        assert translate_capability(canonical_id) == canonical_id


# ---------------------------------------------------------------------------
# Unknown / rejected handling (fail safely)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rejected_id", ["fast_general", "frontier_escalation"])
def test_rejected_legacy_capabilities_raise_specific_error(rejected_id):
    assert rejected_id in LEGACY_B_SIDE_CAPABILITY_VALUES
    assert rejected_id not in KNOWN_CAPABILITIES
    with pytest.raises(RejectedExternalCapabilityError) as exc_info:
        translate_capability(rejected_id)
    # Error message must explain *why*, not just that it's unrecognized.
    assert REJECTED_EXTERNAL_CAPABILITIES[rejected_id] in str(exc_info.value)


def test_rejected_capabilities_table_matches_the_two_non_overlapping_legacy_values():
    non_overlap = LEGACY_B_SIDE_CAPABILITY_VALUES - KNOWN_CAPABILITIES
    assert set(REJECTED_EXTERNAL_CAPABILITIES.keys()) == non_overlap


def test_genuinely_unknown_capability_raises_unknown_error():
    with pytest.raises(UnknownExternalCapabilityError):
        translate_capability("totally-made-up-capability")


def test_unknown_error_is_not_raised_for_rejected_ids():
    # Rejected and unknown are deliberately distinct failure modes.
    with pytest.raises(RejectedExternalCapabilityError):
        translate_capability("fast_general")


# ---------------------------------------------------------------------------
# Duplicate / alias behavior
# ---------------------------------------------------------------------------

def test_translate_capabilities_deduplicates_canonical_output():
    # "coding" (already canonical) and a hypothetical external alias that
    # maps to the same canonical id must not produce two entries.
    result = translate_capabilities(["coding", "coding", "reasoning"])
    assert result == ["coding", "reasoning"]


def test_translate_capabilities_preserves_first_seen_order():
    result = translate_capabilities(["vision", "coding", "vision", "planning"])
    assert result == ["vision", "coding", "planning"]


def test_translate_capabilities_raises_on_first_bad_entry():
    with pytest.raises(RejectedExternalCapabilityError):
        translate_capabilities(["coding", "fast_general", "reasoning"])


def test_translate_capabilities_empty_input():
    assert translate_capabilities([]) == []


# ---------------------------------------------------------------------------
# Deterministic output
# ---------------------------------------------------------------------------

def test_translation_is_deterministic_across_repeated_calls():
    for _ in range(5):
        assert translate_capability("coding") == "coding"
        assert translate_capabilities(["vision", "coding", "vision"]) == ["vision", "coding"]


def test_translation_never_returns_a_non_canonical_value():
    for external_id in EXTERNAL_TO_CANONICAL:
        assert translate_capability(external_id) in KNOWN_CAPABILITIES

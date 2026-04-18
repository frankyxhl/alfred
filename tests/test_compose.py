"""Tests for core/compose.py (FXA-2205 PR4)."""

import pytest


class TestTokenize:
    """Tests for tokenize() function."""

    def test_tokenize_basic_lowercase(self):
        """Tokenize converts to lowercase."""
        from fx_alfred.core.compose import tokenize

        result = tokenize("FXA-2117 PRP")
        assert "fxa-2117" in result
        assert "prp" in result

    def test_tokenize_strips_punctuation(self):
        """Tokenize strips string.punctuation from each token."""
        from fx_alfred.core.compose import tokenize

        # "FXA-2117!" → "fxa-2117" (exclamation stripped, hyphen kept as not in string.punctuation)
        result = tokenize("FXA-2117! Please.")
        assert "fxa-2117" in result
        # "please" is in STOPWORDS, so it should be dropped
        assert "please" not in result

    def test_tokenize_drops_stopwords(self):
        """Tokenize drops stopwords from the fixed set."""
        from fx_alfred.core.compose import tokenize, STOPWORDS

        # Test that stopwords are dropped
        result = tokenize(
            "the a an is are was were be been being to for of in on at by with from"
        )
        # All these are stopwords, should result in empty set
        assert result == frozenset()

        # Verify STOPWORDS contains expected words
        assert "the" in STOPWORDS
        assert "a" in STOPWORDS
        assert "is" in STOPWORDS
        assert "to" in STOPWORDS
        assert "for" in STOPWORDS

    def test_tokenize_drops_empty(self):
        """Tokenize drops empty tokens after stripping."""
        from fx_alfred.core.compose import tokenize

        # "!!!" becomes empty after stripping punctuation
        result = tokenize("!!! ??? ...")
        assert result == frozenset()

    def test_tokenize_returns_frozenset(self):
        """Tokenize returns a frozenset (immutable, deduplicated)."""
        from fx_alfred.core.compose import tokenize

        result = tokenize("test test TEST")
        assert isinstance(result, frozenset)
        # Deduplicated
        assert len(result) == 1
        assert "test" in result

    def test_tokenize_determinism(self):
        """Same input → same output × 100 calls (determinism guarantee)."""
        from fx_alfred.core.compose import tokenize

        inputs = ["Implement FXA-2117 PRP, please."]
        for inp in inputs:
            results = [tokenize(inp) for _ in range(100)]
            first = results[0]
            for r in results[1:]:
                assert r == first, f"Non-deterministic result for {inp!r}"


class TestBigrams:
    """Tests for bigrams() function."""

    def test_bigrams_adjacent_pairs(self):
        """Bigrams creates hyphen-joined pairs from adjacent tokens."""
        from fx_alfred.core.compose import bigrams

        # Input is a list of tokens in order
        result = bigrams(["code", "change", "review"])
        assert "code-change" in result
        assert "change-review" in result
        assert len(result) == 2

    def test_bigrams_single_token_empty(self):
        """Bigrams with single token returns empty set."""
        from fx_alfred.core.compose import bigrams

        result = bigrams(["single"])
        assert result == frozenset()

    def test_bigrams_empty_input(self):
        """Bigrams with empty input returns empty set."""
        from fx_alfred.core.compose import bigrams

        result = bigrams([])
        assert result == frozenset()

    def test_bigrams_returns_frozenset(self):
        """Bigrams returns a frozenset."""
        from fx_alfred.core.compose import bigrams

        result = bigrams(["a", "b", "c"])
        assert isinstance(result, frozenset)


class TestComposeOrder:
    """Tests for compose_order() - Kahn's topological sort with tiebreak."""

    def test_compose_order_single_sop(self):
        """Single SOP returns list with just that SOP."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        doc = Document(
            prefix="COR",
            acid="1500",
            type_code="SOP",
            title="TDD",
            source="pkg",
            directory="rules/COR-1500-SOP-TDD.md",
        )
        result = compose_order([doc])
        assert len(result) == 1
        assert result[0] == doc

    def test_compose_order_independent_layer_tiebreak(self):
        """Independent SOPs (no edges) → layer priority (PKG→USR→PRJ), then ASCII order."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        # Create three independent SOPs from different layers
        pkg_doc = Document(
            prefix="COR",
            acid="1500",
            type_code="SOP",
            title="TDD",
            source="pkg",
            directory="rules/COR-1500-SOP-TDD.md",
        )
        usr_doc = Document(
            prefix="ALF",
            acid="2207",
            type_code="SOP",
            title="Routing",
            source="usr",
            directory="~/.alfred/ALF-2207-SOP-Routing.md",
        )
        prj_doc = Document(
            prefix="FXA",
            acid="2125",
            type_code="SOP",
            title="Routing",
            source="prj",
            directory="rules/FXA-2125-SOP-Routing.md",
        )

        # Input order should not matter; output should be PKG → USR → PRJ
        result = compose_order([prj_doc, usr_doc, pkg_doc])
        assert result[0].source == "pkg"
        assert result[1].source == "usr"
        assert result[2].source == "prj"

    def test_compose_order_ascii_tiebreak_same_layer(self):
        """Same layer, no edges → ASCII order by SOP-ID."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        # Three PKG SOPs with different ACIDs
        doc1 = Document(
            prefix="COR",
            acid="1602",
            type_code="SOP",
            title="Review",
            source="pkg",
            directory="rules/COR-1602-SOP-Review.md",
        )
        doc2 = Document(
            prefix="COR",
            acid="1500",
            type_code="SOP",
            title="TDD",
            source="pkg",
            directory="rules/COR-1500-SOP-TDD.md",
        )
        doc3 = Document(
            prefix="COR",
            acid="1600",
            type_code="SOP",
            title="General",
            source="pkg",
            directory="rules/COR-1600-SOP-General.md",
        )

        # ASCII order: COR-1500 < COR-1600 < COR-1602
        result = compose_order([doc3, doc1, doc2])
        assert result[0].acid == "1500"
        assert result[1].acid == "1600"
        assert result[2].acid == "1602"

    def test_compose_order_typed_chain_a_to_b_to_c(self):
        """Typed chain A→B→C via workflow_edges respects edge order even when ASCII would reverse."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        # Choose doc IDs whose ASCII order would be C < B < A, so edges must win.
        doc_a = Document(
            prefix="TST",
            acid="9003",
            type_code="SOP",
            title="StepA",
            source="pkg",
            directory="rules/TST-9003-SOP-StepA.md",
        )
        doc_b = Document(
            prefix="TST",
            acid="9002",
            type_code="SOP",
            title="StepB",
            source="pkg",
            directory="rules/TST-9002-SOP-StepB.md",
        )
        doc_c = Document(
            prefix="TST",
            acid="9001",
            type_code="SOP",
            title="StepC",
            source="pkg",
            directory="rules/TST-9001-SOP-StepC.md",
        )

        # A.output="ax" → B.input="ax"; B.output="bx" → C.input="bx"
        edges = {
            "TST-9003": (None, "ax"),
            "TST-9002": ("ax", "bx"),
            "TST-9001": ("bx", None),
        }

        result = compose_order([doc_a, doc_b, doc_c], edges)
        # Despite ASCII order 9001 < 9002 < 9003, typed edges force A→B→C.
        assert [d.acid for d in result] == ["9003", "9002", "9001"]

    def test_compose_order_edges_override_ascii_for_two_docs(self):
        """Typed edge A.output → B.input forces [A, B] even when ASCII would return [B, A]."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        # ASCII: TST-7002 < TST-7009, so without edges result would be [7002, 7009].
        doc_a = Document(
            prefix="TST",
            acid="7009",
            type_code="SOP",
            title="First",
            source="pkg",
            directory="rules/TST-7009-SOP-First.md",
        )
        doc_b = Document(
            prefix="TST",
            acid="7002",
            type_code="SOP",
            title="Second",
            source="pkg",
            directory="rules/TST-7002-SOP-Second.md",
        )

        edges = {
            "TST-7009": (None, "draft"),
            "TST-7002": ("draft", None),
        }

        result = compose_order([doc_a, doc_b], edges)
        assert [d.acid for d in result] == ["7009", "7002"]

        # Control: without edges, ASCII tiebreak restores [7002, 7009]
        result_no_edges = compose_order([doc_a, doc_b])
        assert [d.acid for d in result_no_edges] == ["7002", "7009"]

    def test_compose_order_real_cycle_raises_click_exception(self):
        """True cycle A→B→A in Workflow input/output edges raises ClickException."""
        import click

        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        doc_a = Document(
            prefix="TST",
            acid="8001",
            type_code="SOP",
            title="StepA",
            source="pkg",
            directory="rules/TST-8001-SOP-StepA.md",
        )
        doc_b = Document(
            prefix="TST",
            acid="8002",
            type_code="SOP",
            title="StepB",
            source="pkg",
            directory="rules/TST-8002-SOP-StepB.md",
        )

        # A.output=x → B.input=x AND B.output=y → A.input=y → cycle
        edges = {
            "TST-8001": ("y", "x"),
            "TST-8002": ("x", "y"),
        }

        with pytest.raises(click.ClickException) as exc_info:
            compose_order([doc_a, doc_b], edges)

        msg = str(exc_info.value)
        assert "cycle" in msg.lower() or "cyclic" in msg.lower() or "TST-8001" in msg

    def test_compose_order_edge_doc_not_in_map_is_skipped(self):
        """workflow_edges entries whose doc_id is absent from candidates are ignored."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        doc = Document(
            prefix="TST",
            acid="5001",
            type_code="SOP",
            title="Solo",
            source="pkg",
            directory="rules/TST-5001-SOP-Solo.md",
        )

        # Edge entries reference phantom docs not present in candidates
        edges = {
            "TST-5001": (None, "out1"),
            "TST-9999": ("out1", None),  # phantom
            "TST-8888": ("something", "out1"),  # phantom
        }

        result = compose_order([doc], edges)
        assert len(result) == 1
        assert result[0].acid == "5001"


class TestResolveSopsFromTask:
    """Tests for resolve_sops_from_task() - full C1 algorithm."""

    def test_resolve_one_tag_match_returns_with_always_prepended(self):
        """One tag match → returns it + always-included SOPs prepended."""
        from fx_alfred.core.compose import resolve_sops_from_task
        from fx_alfred.core.document import Document

        # Create mock SOPs with task tags and always-included status
        tagged_doc = Document(
            prefix="TST",
            acid="1500",
            type_code="SOP",
            title="Tagged",
            source="pkg",
            directory="rules/TST-1500-SOP-Tagged.md",
        )
        always_doc = Document(
            prefix="TST",
            acid="1103",
            type_code="SOP",
            title="Always",
            source="pkg",
            directory="rules/TST-1103-SOP-Always.md",
        )

        all_sops = [
            (tagged_doc, frozenset(["implement", "tdd"]), False),
            (always_doc, frozenset(), True),
        ]

        # Task "implement" should match tagged_doc, plus always_doc
        ordered_ids, provenance = resolve_sops_from_task(
            "implement feature", all_sops, []
        )

        # Both should be included
        assert "TST-1500" in ordered_ids
        assert "TST-1103" in ordered_ids
        # Always should be in always provenance
        assert "TST-1103" in provenance["always"]
        # Tagged should be in auto provenance
        assert "TST-1500" in provenance["auto"]

    def test_resolve_bigram_probe_matches_hyphenated_tag(self):
        """Bigram probe 'code change' matches 'code-change' tag."""
        from fx_alfred.core.compose import tokenize_ordered, bigrams

        # Test the tokenization + bigram logic with original order preserved
        tokens_list = tokenize_ordered("code change feature")
        bg = bigrams(tokens_list)
        assert "code-change" in bg
        assert "change-feature" in bg

    def test_resolve_empty_task_no_positional_raises_exit_2(self):
        """Empty tag match + no positional → ClickException exit 2 with diagnostic."""
        from fx_alfred.core.compose import resolve_sops_from_task
        from fx_alfred.core.document import Document
        import click

        # Create only always-included SOP with no matching tags
        always_doc = Document(
            prefix="TST",
            acid="1103",
            type_code="SOP",
            title="Always",
            source="pkg",
            directory="rules/TST-1103-SOP-Always.md",
        )

        all_sops = [(always_doc, frozenset(), True)]

        # "xyzzy rare unmatched" should match nothing
        with pytest.raises(click.ClickException) as exc_info:
            resolve_sops_from_task("xyzzy rare unmatched", all_sops, [])

        assert exc_info.value.exit_code == 2
        assert "matched 0 tagged SOPs" in str(exc_info.value)

    def test_resolve_positional_and_task_union_deduped(self):
        """Positional IDs + tag matches → union, de-duplicated."""
        from fx_alfred.core.compose import resolve_sops_from_task
        from fx_alfred.core.document import Document

        # Create multiple SOPs
        tagged_doc = Document(
            prefix="TST",
            acid="1500",
            type_code="SOP",
            title="Tagged",
            source="pkg",
            directory="rules/TST-1500-SOP-Tagged.md",
        )
        explicit_doc = Document(
            prefix="TST",
            acid="7001",
            type_code="SOP",
            title="Explicit",
            source="pkg",
            directory="rules/TST-7001-SOP-Explicit.md",
        )
        always_doc = Document(
            prefix="TST",
            acid="1103",
            type_code="SOP",
            title="Always",
            source="pkg",
            directory="rules/TST-1103-SOP-Always.md",
        )

        all_sops = [
            (tagged_doc, frozenset(["implement"]), False),
            (explicit_doc, frozenset(["other"]), False),
            (always_doc, frozenset(), True),
        ]

        # Task "implement" matches tagged_doc, plus positional explicit_doc
        ordered_ids, provenance = resolve_sops_from_task(
            "implement", all_sops, ["TST-7001"]
        )

        # All three should be included, de-duplicated
        assert len(ordered_ids) == len(set(ordered_ids))  # No duplicates
        assert "TST-1500" in ordered_ids  # Tag matched
        assert "TST-7001" in ordered_ids  # Explicit
        assert "TST-1103" in ordered_ids  # Always
        # Check provenance
        assert "TST-1103" in provenance["always"]
        assert "TST-7001" in provenance["explicit"]
        assert "TST-1500" in provenance["auto"]

    def test_resolve_always_included_prepended(self):
        """Always-included SOPs are always prepended."""
        from fx_alfred.core.compose import resolve_sops_from_task
        from fx_alfred.core.document import Document

        # Create SOPs where always is PKG layer (should come first)
        tagged_doc = Document(
            prefix="TST",
            acid="1500",
            type_code="SOP",
            title="Tagged",
            source="prj",
            directory="rules/TST-1500-SOP-Tagged.md",
        )
        always_doc = Document(
            prefix="TST",
            acid="1103",
            type_code="SOP",
            title="Always",
            source="pkg",
            directory="rules/TST-1103-SOP-Always.md",
        )

        all_sops = [
            (tagged_doc, frozenset(["implement"]), False),
            (always_doc, frozenset(), True),
        ]

        # Task "implement" matches tagged_doc, plus always_doc
        ordered_ids, provenance = resolve_sops_from_task("implement", all_sops, [])

        # Always should be first (PKG layer priority)
        assert ordered_ids[0] == "TST-1103"
        assert "TST-1103" in provenance["always"]
        assert "TST-1500" in provenance["auto"]


class TestStopwordsConstant:
    """Tests for STOPWORDS constant."""

    def test_stopwords_is_frozenset(self):
        """STOPWORDS is a frozenset."""
        from fx_alfred.core.compose import STOPWORDS

        assert isinstance(STOPWORDS, frozenset)

    def test_stopwords_contains_expected_words(self):
        """STOPWORDS contains the verbatim set from the spec."""
        from fx_alfred.core.compose import STOPWORDS

        expected = {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "to",
            "for",
            "of",
            "in",
            "on",
            "at",
            "by",
            "with",
            "from",
            "and",
            "or",
            "but",
            "if",
            "then",
            "else",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "do",
            "does",
            "did",
            "please",
            "need",
            "needs",
            "needed",
        }
        assert STOPWORDS == expected


class TestComposeOrderWithEdges:
    """Tests for compose_order with typed workflow edges."""

    def test_compose_order_two_node_chain(self):
        """Two nodes with A.output == B.input → A before B."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        doc_a = Document(
            prefix="TST",
            acid="6001",
            type_code="SOP",
            title="StepA",
            source="pkg",
            directory="rules/TST-6001-SOP-StepA.md",
        )
        doc_b = Document(
            prefix="TST",
            acid="6002",
            type_code="SOP",
            title="StepB",
            source="pkg",
            directory="rules/TST-6002-SOP-StepB.md",
        )

        # A outputs "reviewed", B inputs "reviewed"
        workflow_edges = {
            "TST-6001": (None, "reviewed"),
            "TST-6002": ("reviewed", None),
        }

        result = compose_order([doc_a, doc_b], workflow_edges)
        # A should come before B because A.output == B.input
        assert result[0].acid == "6001"
        assert result[1].acid == "6002"

    def test_compose_order_three_node_chain(self):
        """Three nodes with A→B→C chain."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        doc_a = Document(
            prefix="TST",
            acid="6001",
            type_code="SOP",
            title="StepA",
            source="pkg",
            directory="rules/TST-6001-SOP-StepA.md",
        )
        doc_b = Document(
            prefix="TST",
            acid="6002",
            type_code="SOP",
            title="StepB",
            source="pkg",
            directory="rules/TST-6002-SOP-StepB.md",
        )
        doc_c = Document(
            prefix="TST",
            acid="6003",
            type_code="SOP",
            title="StepC",
            source="pkg",
            directory="rules/TST-6003-SOP-StepC.md",
        )

        # A→B→C chain: A.output == B.input, B.output == C.input
        workflow_edges = {
            "TST-6001": (None, "draft"),
            "TST-6002": ("draft", "reviewed"),
            "TST-6003": ("reviewed", None),
        }

        result = compose_order([doc_c, doc_a, doc_b], workflow_edges)
        # Order should be A → B → C regardless of input order
        assert result[0].acid == "6001"
        assert result[1].acid == "6002"
        assert result[2].acid == "6003"

    def test_compose_order_cycle_raises_click_exception(self):
        """True cycle A→B→A raises ClickException."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document
        import click

        doc_a = Document(
            prefix="TST",
            acid="6001",
            type_code="SOP",
            title="StepA",
            source="pkg",
            directory="rules/TST-6001-SOP-StepA.md",
        )
        doc_b = Document(
            prefix="TST",
            acid="6002",
            type_code="SOP",
            title="StepB",
            source="pkg",
            directory="rules/TST-6002-SOP-StepB.md",
        )

        # Cycle: A.output == B.input, B.output == A.input
        workflow_edges = {
            "TST-6001": ("done", "reviewed"),
            "TST-6002": ("reviewed", "done"),
        }

        with pytest.raises(click.ClickException, match="Workflow cycle detected"):
            compose_order([doc_a, doc_b], workflow_edges)

    def test_compose_order_partial_edges(self):
        """Some nodes with edges, others independent."""
        from fx_alfred.core.compose import compose_order
        from fx_alfred.core.document import Document

        doc_a = Document(
            prefix="TST",
            acid="6001",
            type_code="SOP",
            title="StepA",
            source="pkg",
            directory="rules/TST-6001-SOP-StepA.md",
        )
        doc_b = Document(
            prefix="TST",
            acid="6002",
            type_code="SOP",
            title="StepB",
            source="pkg",
            directory="rules/TST-6002-SOP-StepB.md",
        )
        doc_c = Document(
            prefix="TST",
            acid="6003",
            type_code="SOP",
            title="StepC",
            source="pkg",
            directory="rules/TST-6003-SOP-StepC.md",
        )

        # A→B edge, C is independent
        workflow_edges = {
            "TST-6001": (None, "reviewed"),
            "TST-6002": ("reviewed", None),
            "TST-6003": (None, None),
        }

        result = compose_order([doc_c, doc_a, doc_b], workflow_edges)
        # A should come before B, C can be anywhere (but ASCII tiebreak puts 6001, 6002, 6003)
        # Actually, A→B edge means A must come before B, but C is independent
        # So the order should respect the edge, with C positioned by ASCII tiebreak
        # Since A has in_degree 0, and C has in_degree 0, they both start available
        # Sorted by layer+ASCII: A (6001) < C (6003), so A first, then C or B
        # A is processed first, then B's in_degree becomes 0
        # Queue has [C (6003), B (6002)] - sorted: B < C
        # So order is A, B, C
        assert result[0].acid == "6001"  # A
        assert result[1].acid == "6002"  # B
        assert result[2].acid == "6003"  # C


class TestCoverageFills:
    """Extra targeted tests to exercise untested branches."""

    def test_tokenize_ordered_skips_stopwords_and_empty(self):
        """tokenize_ordered drops stopwords and empty-after-strip tokens."""
        from fx_alfred.core.compose import tokenize_ordered

        # "the" and "is" are stopwords; "!!!" strips to empty
        result = tokenize_ordered("the implement !!! is fxa-2117")
        assert "the" not in result
        assert "is" not in result
        assert "" not in result
        assert "implement" in result
        assert "fxa-2117" in result

    def test_tokenize_ordered_dedupes_preserving_first_occurrence(self):
        """Duplicate tokens are kept once, at their first position."""
        from fx_alfred.core.compose import tokenize_ordered

        result = tokenize_ordered("code change code change feature")
        assert result == ["code", "change", "feature"]

    def test_resolve_explicit_id_not_found_raises_clickexception(self):
        """Unknown positional SOP ID in --task mode → ClickException 'SOP X not found'."""
        import click

        from fx_alfred.core.compose import resolve_sops_from_task
        from fx_alfred.core.document import Document

        doc = Document(
            prefix="TST",
            acid="1103",
            type_code="SOP",
            title="Always",
            source="pkg",
            directory="rules/TST-1103-SOP-Always.md",
        )
        all_sops = [(doc, frozenset(), True)]

        with pytest.raises(click.ClickException) as exc_info:
            resolve_sops_from_task("implement", all_sops, ["BAD-9999"])

        assert "BAD-9999" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()


class TestResolveSopsFromTaskBotP2Regression:
    """Regression tests for PR #46 bot-P2 fix (chatgpt-codex-connector).

    The empty-match check must be based on tag_cands + positional_set only,
    NOT on `candidates == always_set`. Otherwise, a SOP that is BOTH
    always-included AND has a matching Task tag wrongly triggers exit 2.
    """

    def test_always_included_with_tag_match_does_not_trigger_empty_error(self):
        """SOP that is BOTH Always included AND has matching tag → returns successfully."""
        from fx_alfred.core.compose import resolve_sops_from_task
        from fx_alfred.core.document import Document

        # Synthetic SOP that is both always-included AND has matching tag 'foo'.
        always_and_tagged_doc = Document(
            prefix="TST",
            acid="9100",
            type_code="SOP",
            title="AlwaysAndTagged",
            source="pkg",
            directory="rules/TST-9100-SOP-AlwaysAndTagged.md",
        )

        # (doc, task_tags, always_included)
        # Only one SOP in the corpus. It has tag 'foo' AND always_included=True.
        all_sops = [
            (always_and_tagged_doc, frozenset(["foo", "bar"]), True),
        ]

        # Task "foo bar" tokenizes to {foo, bar}; tag_cands = {TST-9100}.
        # always_set also = {TST-9100}. Pre-fix: candidates == always_set → exit 2.
        # Post-fix: tag_cands is non-empty → compose successfully.
        ordered_ids, provenance = resolve_sops_from_task("foo bar", all_sops, [])

        # No exception was raised; SOP is in the plan.
        assert "TST-9100" in ordered_ids
        # Always-included provenance wins the classification for dual-class SOPs.
        assert "TST-9100" in provenance["always"]

    def test_empty_match_still_raises_when_no_tags_and_no_positional(self):
        """Empty tag match + no positional → ClickException exit 2 (fail-closed preserved)."""
        import click

        from fx_alfred.core.compose import resolve_sops_from_task
        from fx_alfred.core.document import Document

        # SOP with no tags, not always-included.
        untagged_doc = Document(
            prefix="TST",
            acid="9200",
            type_code="SOP",
            title="Untagged",
            source="pkg",
            directory="rules/TST-9200-SOP-Untagged.md",
        )

        all_sops = [
            (untagged_doc, frozenset(), False),  # No tags, not always-included
        ]

        # "xyzzy unmatched" matches no tags; no positional → must fail-closed.
        with pytest.raises(click.ClickException) as exc_info:
            resolve_sops_from_task("xyzzy unmatched", all_sops, [])

        assert exc_info.value.exit_code == 2
        assert "matched 0 tagged SOPs" in str(exc_info.value)

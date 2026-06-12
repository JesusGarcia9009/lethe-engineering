from lethe.evals.needle import run_needle


def test_needle_survives_compaction_and_paging():
    s = run_needle(steps=50)
    # the planted fact is recovered after being buried and paged out
    assert s["needle_recovered"] is True
    # the working set stayed under budget throughout the run
    assert s["max_tokens_with_lethe"] <= s["target_tokens"]
    # LETHE genuinely saved tokens vs sending everything
    assert s["tokens_without_lethe"] > s["tokens_with_lethe"]

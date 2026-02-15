"""A/B benchmark: SQLite FTS5 vs Qdrant text search vs Qdrant hybrid.

Usage:
    uv run python bench/ab_fts_vs_qdrant.py

Requires a populated memory store (run `cmk remember` a few times first).
Set MEMORY_STORE_PATH or uses default ~/.claude-memory.
"""

import os
import sys
import time

# Ensure package is importable from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_memory_kit.config import get_store_path
from claude_memory_kit.store.sqlite import SqliteStore
from claude_memory_kit.store.vectors import VectorStore


def run_bench():
    store_path = get_store_path()
    db = SqliteStore(store_path)
    db.migrate()
    vectors = VectorStore(store_path)
    vectors.ensure_collection()

    # Count memories to verify there's data
    total = db.count_memories(user_id="local")
    print(f"store: {store_path}")
    print(f"memories: {total}")
    if total == 0:
        print("no memories found. add some with `cmk remember` first.")
        return

    # Sample some content words from existing memories for realistic queries
    sample_mems = db.list_memories(limit=20, user_id="local")
    auto_queries = []
    for mem in sample_mems[:10]:
        words = mem.content.split()
        if len(words) >= 3:
            # Pick a 2-3 word slice from the middle
            mid = len(words) // 2
            auto_queries.append(" ".join(words[mid:mid+2]))

    queries = auto_queries or ["python", "project", "preference", "remember"]
    # Deduplicate
    queries = list(dict.fromkeys(queries))

    print(f"\nrunning {len(queries)} queries across 3 search backends\n")
    print(f"{'query':<30} {'FTS5':>8} {'Q-text':>8} {'hybrid':>8}  overlap")
    print("-" * 80)

    fts_total_ms = 0.0
    qtext_total_ms = 0.0
    hybrid_total_ms = 0.0
    overlap_ratios = []

    for q in queries:
        # A: SQLite FTS5
        t0 = time.perf_counter()
        try:
            fts_results = db.search_fts(q, limit=10, user_id="local")
        except Exception:
            fts_results = []
        fts_ms = (time.perf_counter() - t0) * 1000

        # B: Qdrant text index
        t0 = time.perf_counter()
        try:
            qtext_results = vectors.search_text(q, limit=10, user_id="local")
        except Exception:
            qtext_results = []
        qtext_ms = (time.perf_counter() - t0) * 1000

        # C: Qdrant hybrid (dense + sparse RRF)
        t0 = time.perf_counter()
        try:
            hybrid_results = vectors.search(q, limit=10, user_id="local")
        except Exception:
            hybrid_results = []
        hybrid_ms = (time.perf_counter() - t0) * 1000

        fts_ids = {m.id for m in fts_results}
        qtext_ids = {mid for mid, _ in qtext_results}
        hybrid_ids = {mid for mid, _ in hybrid_results}
        all_ids = fts_ids | qtext_ids

        if all_ids:
            overlap = len(fts_ids & qtext_ids) / len(all_ids)
        else:
            overlap = 1.0

        overlap_ratios.append(overlap)
        fts_total_ms += fts_ms
        qtext_total_ms += qtext_ms
        hybrid_total_ms += hybrid_ms

        q_display = q[:28] + ".." if len(q) > 30 else q
        print(
            f"{q_display:<30} "
            f"{len(fts_results):>3} {fts_ms:>4.1f}ms "
            f"{len(qtext_results):>3} {qtext_ms:>4.1f}ms "
            f"{len(hybrid_results):>3} {hybrid_ms:>4.1f}ms  "
            f"fts/qtext={overlap:.0%}"
        )

    n = len(queries)
    avg_overlap = sum(overlap_ratios) / n if n else 0

    print("-" * 80)
    print(f"{'avg':<30} {'':>3} {fts_total_ms/n:>4.1f}ms {'':>3} {qtext_total_ms/n:>4.1f}ms {'':>3} {hybrid_total_ms/n:>4.1f}ms  overlap={avg_overlap:.0%}")
    print()

    if avg_overlap > 0.8:
        print("verdict: high overlap. qdrant text index is a safe FTS5 replacement.")
    elif avg_overlap > 0.5:
        print("verdict: moderate overlap. qdrant text index catches most, but FTS5 finds some extras.")
    else:
        print("verdict: low overlap. FTS5 and qdrant text index return different results. keep both or investigate.")

    print()
    print("notes:")
    print("  - FTS5 supports boolean operators (AND/OR/NOT), qdrant text does substring matching")
    print("  - hybrid search (dense+sparse) is the primary path, text is only a fallback")
    print("  - if hybrid already returns results, neither FTS5 nor text search runs")


if __name__ == "__main__":
    run_bench()

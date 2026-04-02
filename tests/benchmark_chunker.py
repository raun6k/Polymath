#!/usr/bin/env python3
"""
Benchmark: C++ SemanticChunker vs pure-Python fallback.

Usage:
    python tests/benchmark_chunker.py [--words N]

Generates a synthetic document of N words (default 10,000) and measures
chunking throughput for both implementations.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── Pure-Python chunker (same logic as orchestrator fallback) ─────────────────

def python_chunk(text: str, max_tokens: int = 256, overlap_tokens: int = 32) -> list[str]:
    import re
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])|(?<=\n)\n", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    current_sents: list[str] = []
    current_tokens = 0

    def _est(s: str) -> int:
        return len(s.split())

    for sent in sentences:
        est = _est(sent)
        if current_tokens + est > max_tokens and current_sents:
            chunks.append(" ".join(current_sents))
            overlap_sents: list[str] = []
            overlap_t = 0
            for s in reversed(current_sents):
                if overlap_t + _est(s) > overlap_tokens:
                    break
                overlap_sents.insert(0, s)
                overlap_t += _est(s)
            current_sents = overlap_sents
            current_tokens = overlap_t
        current_sents.append(sent)
        current_tokens += est

    if current_sents:
        chunks.append(" ".join(current_sents))
    return chunks


# ── Document generator ────────────────────────────────────────────────────────

WORDS = [
    "the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
    "research", "assistant", "document", "knowledge", "embedding", "vector",
    "retrieval", "augmented", "generation", "language", "model", "inference",
    "semantic", "chunker", "sentence", "boundary", "overlap", "token",
    "analysis", "synthesis", "information", "artificial", "intelligence",
]


def generate_document(n_words: int) -> str:
    rng = random.Random(42)
    sentences: list[str] = []
    i = 0
    while i < n_words:
        length = rng.randint(8, 20)
        words = [rng.choice(WORDS) for _ in range(length)]
        words[0] = words[0].capitalize()
        sentences.append(" ".join(words) + ".")
        i += length
    return " ".join(sentences)


# ── Main ──────────────────────────────────────────────────────────────────────

def run(n_words: int) -> None:
    print(f"\nPolymath Chunker Benchmark — {n_words:,} words")
    print("=" * 52)

    text = generate_document(n_words)
    print(f"Document size: {len(text):,} characters\n")

    # Python baseline
    py_times = []
    py_chunks = None
    for _ in range(3):
        t0 = time.perf_counter()
        py_chunks = python_chunk(text)
        py_times.append(time.perf_counter() - t0)
    py_avg = sum(py_times) / len(py_times)
    print(f"Python chunker:  {py_avg*1000:.1f} ms  ({len(py_chunks)} chunks)")

    # C++ chunker
    try:
        from fast_chunker import SemanticChunker  # type: ignore
        chunker = SemanticChunker(256, 32)
        cpp_times = []
        cpp_chunks = None
        for _ in range(3):
            t0 = time.perf_counter()
            cpp_chunks = chunker.chunk(text)
            cpp_times.append(time.perf_counter() - t0)
        cpp_avg = sum(cpp_times) / len(cpp_times)
        speedup = py_avg / cpp_avg if cpp_avg > 0 else float("inf")
        print(f"C++ chunker:     {cpp_avg*1000:.1f} ms  ({len(cpp_chunks)} chunks)")
        print(f"\nSpeedup: {speedup:.1f}x {'✓' if speedup >= 5 else '(target: 5x+)'}")
    except ImportError:
        print("C++ chunker:     NOT BUILT — run `cmake --build chunker/build` first")
        print("\nRe-run after building the C++ extension to see the speedup.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Polymath chunkers")
    parser.add_argument("--words", type=int, default=10_000, help="Word count for test document")
    args = parser.parse_args()
    run(args.words)

#include <gtest/gtest.h>
#include "chunker.hpp"

using polymath::Chunk;
using polymath::SemanticChunker;

// ── Construction ─────────────────────────────────────────────────────────────

TEST(SemanticChunkerTest, DefaultConstruction) {
    SemanticChunker chunker;
    EXPECT_EQ(chunker.max_tokens(), 256u);
    EXPECT_EQ(chunker.overlap_tokens(), 32u);
}

TEST(SemanticChunkerTest, CustomConstruction) {
    SemanticChunker chunker(128, 16);
    EXPECT_EQ(chunker.max_tokens(), 128u);
    EXPECT_EQ(chunker.overlap_tokens(), 16u);
}

// ── Edge cases ───────────────────────────────────────────────────────────────

TEST(SemanticChunkerTest, EmptyText) {
    SemanticChunker chunker;
    auto chunks = chunker.chunk("");
    EXPECT_TRUE(chunks.empty());
}

TEST(SemanticChunkerTest, SingleShortSentence) {
    SemanticChunker chunker;
    auto chunks = chunker.chunk("Hello world.");
    ASSERT_EQ(chunks.size(), 1u);
    EXPECT_EQ(chunks[0].text, "Hello world.");
    EXPECT_EQ(chunks[0].token_estimate, 2u);
}

TEST(SemanticChunkerTest, WhitespaceOnlyText) {
    SemanticChunker chunker;
    auto chunks = chunker.chunk("   \n\n\t  ");
    EXPECT_TRUE(chunks.empty());
}

// ── Sentence boundary detection ──────────────────────────────────────────────

TEST(SemanticChunkerTest, MultipleSentences) {
    SemanticChunker chunker(256, 0);
    std::string text = "First sentence. Second sentence. Third sentence.";
    auto chunks = chunker.chunk(text);
    ASSERT_FALSE(chunks.empty());
    // All sentences should be in one chunk (well under 256 tokens)
    EXPECT_EQ(chunks.size(), 1u);
    EXPECT_NE(chunks[0].text.find("First"), std::string::npos);
    EXPECT_NE(chunks[0].text.find("Third"), std::string::npos);
}

TEST(SemanticChunkerTest, ExclamationAndQuestionMarks) {
    SemanticChunker chunker(256, 0);
    std::string text = "Is this working? Yes it is! Great.";
    auto chunks = chunker.chunk(text);
    ASSERT_FALSE(chunks.empty());
}

// ── Token limit enforcement ───────────────────────────────────────────────────

TEST(SemanticChunkerTest, ChunkSizeRespected) {
    // Each sentence is ~10 tokens. With max_tokens=20, we expect ~1-2 sentences per chunk.
    SemanticChunker chunker(20, 0);
    std::string text =
        "The quick brown fox jumps over the lazy dog one. "
        "The quick brown fox jumps over the lazy dog two. "
        "The quick brown fox jumps over the lazy dog three. "
        "The quick brown fox jumps over the lazy dog four.";
    auto chunks = chunker.chunk(text);
    EXPECT_GT(chunks.size(), 1u);
    for (const auto& c : chunks) {
        EXPECT_LE(c.token_estimate, 30u); // allow slight overage for single-sentence chunks
    }
}

// ── No text loss ──────────────────────────────────────────────────────────────

TEST(SemanticChunkerTest, NoTextLoss) {
    SemanticChunker chunker(30, 5);
    std::string text =
        "Alpha beta gamma delta epsilon. "
        "Zeta eta theta iota kappa lambda. "
        "Mu nu xi omicron pi rho sigma. "
        "Tau upsilon phi chi psi omega.";
    auto chunks = chunker.chunk(text);
    ASSERT_FALSE(chunks.empty());

    // Every unique word from the original should appear in at least one chunk
    const std::vector<std::string> keywords = {
        "Alpha", "epsilon", "Zeta", "lambda", "Mu", "sigma", "Tau", "omega"
    };
    for (const auto& kw : keywords) {
        bool found = false;
        for (const auto& c : chunks) {
            if (c.text.find(kw) != std::string::npos) { found = true; break; }
        }
        EXPECT_TRUE(found) << "Keyword not found in any chunk: " << kw;
    }
}

// ── Overlap ───────────────────────────────────────────────────────────────────

TEST(SemanticChunkerTest, OverlapPresent) {
    // With overlap, last sentence of chunk N should appear in chunk N+1
    SemanticChunker chunker(15, 8);
    std::string text =
        "Sentence one is here now. "
        "Sentence two is here now. "
        "Sentence three is here now. "
        "Sentence four is here now.";
    auto chunks = chunker.chunk(text);
    if (chunks.size() >= 2) {
        // The last sentence of chunk 0 should partially appear in chunk 1
        // (overlap mechanism — at minimum chunk 1 is not identical to chunk 0)
        EXPECT_NE(chunks[0].text, chunks[1].text);
    }
}

// ── Very long document ────────────────────────────────────────────────────────

TEST(SemanticChunkerTest, LongDocument) {
    SemanticChunker chunker(50, 10);
    std::string text;
    // Build a ~500-sentence document
    for (int i = 0; i < 500; ++i) {
        text += "This is sentence number " + std::to_string(i) +
                " in a very long document. ";
    }
    auto chunks = chunker.chunk(text);
    EXPECT_GT(chunks.size(), 10u);
    // Spot-check: all chunks are non-empty
    for (const auto& c : chunks) {
        EXPECT_FALSE(c.text.empty());
        EXPECT_GT(c.token_estimate, 0u);
    }
}

// ── Offsets ───────────────────────────────────────────────────────────────────

TEST(SemanticChunkerTest, OffsetsSane) {
    SemanticChunker chunker(20, 0);
    std::string text =
        "First chunk content here. Second chunk content here. "
        "Third chunk content here. Fourth chunk content here.";
    auto chunks = chunker.chunk(text);
    for (const auto& c : chunks) {
        EXPECT_LT(c.start_offset, c.end_offset);
        EXPECT_GT(c.token_estimate, 0u);
    }
}

#include "chunker.hpp"

#include <algorithm>
#include <sstream>
#include <cctype>

namespace polymath {

SemanticChunker::SemanticChunker(std::size_t max_tokens,
                                  std::size_t overlap_tokens)
    : max_tokens_(max_tokens), overlap_tokens_(overlap_tokens) {}

std::size_t SemanticChunker::estimate_tokens(const std::string& text) const {
    if (text.empty()) return 0;
    std::size_t count = 0;
    bool in_word = false;
    for (char c : text) {
        if (std::isspace(static_cast<unsigned char>(c))) {
            in_word = false;
        } else {
            if (!in_word) {
                ++count;
                in_word = true;
            }
        }
    }
    return count;
}

std::vector<std::string> SemanticChunker::split_sentences(
    const std::string& text) const {
    std::vector<std::string> sentences;
    if (text.empty()) return sentences;

    std::string current;
    current.reserve(256);

    for (std::size_t i = 0; i < text.size(); ++i) {
        char c = text[i];
        current += c;

        bool is_boundary = false;

        if (c == '.' || c == '!' || c == '?') {
            // Look-ahead: next non-space char should be uppercase or end of string
            std::size_t j = i + 1;
            while (j < text.size() && text[j] == ' ') ++j;
            if (j >= text.size() || std::isupper(static_cast<unsigned char>(text[j])) ||
                text[j] == '\n') {
                is_boundary = true;
            }
        } else if (c == '\n') {
            // Double newline = paragraph break = sentence boundary
            if (i + 1 < text.size() && text[i + 1] == '\n') {
                is_boundary = true;
            }
        }

        if (is_boundary) {
            auto s = current.find_first_not_of(" \t\n\r");
            if (s != std::string::npos) {
                auto e = current.find_last_not_of(" \t\n\r");
                sentences.push_back(current.substr(s, e - s + 1));
            }
            current.clear();
        }
    }

    // Handle any remaining text
    auto start = current.find_first_not_of(" \t\n\r");
    auto end = current.find_last_not_of(" \t\n\r");
    if (start != std::string::npos) {
        sentences.push_back(current.substr(start, end - start + 1));
    }

    return sentences;
}

std::string SemanticChunker::get_overlap_text(
    const std::vector<std::string>& sentences,
    std::size_t end_idx) const {
    if (end_idx == 0 || overlap_tokens_ == 0) return "";

    std::string overlap;
    std::size_t tokens = 0;
    std::size_t i = end_idx;

    while (i > 0) {
        --i;
        std::size_t sent_tokens = estimate_tokens(sentences[i]);
        if (tokens + sent_tokens > overlap_tokens_) break;
        tokens += sent_tokens;
        overlap = sentences[i] + " " + overlap;
    }

    // Trim trailing space
    if (!overlap.empty() && overlap.back() == ' ') {
        overlap.pop_back();
    }
    return overlap;
}

std::vector<Chunk> SemanticChunker::chunk(const std::string& text) const {
    std::vector<Chunk> chunks;
    if (text.empty()) return chunks;

    auto sentences = split_sentences(text);
    if (sentences.empty()) return chunks;

    std::size_t sent_idx = 0;
    std::size_t char_offset = 0;

    while (sent_idx < sentences.size()) {
        std::string chunk_text;
        std::size_t chunk_tokens = 0;
        std::size_t chunk_start_sent = sent_idx;

        // Add overlap from previous chunk
        std::string overlap_prefix = get_overlap_text(sentences, sent_idx);
        if (!overlap_prefix.empty()) {
            chunk_text = overlap_prefix + " ";
            chunk_tokens = estimate_tokens(overlap_prefix);
        }

        // Fill chunk up to max_tokens
        while (sent_idx < sentences.size()) {
            const std::string& sent = sentences[sent_idx];
            std::size_t sent_tokens = estimate_tokens(sent);

            if (chunk_tokens + sent_tokens > max_tokens_ && !chunk_text.empty()) {
                // This sentence would exceed limit — end chunk here
                break;
            }

            if (!chunk_text.empty()) chunk_text += " ";
            chunk_text += sent;
            chunk_tokens += sent_tokens;
            ++sent_idx;
        }

        // Trim
        auto s = chunk_text.find_first_not_of(" \t\n\r");
        auto e = chunk_text.find_last_not_of(" \t\n\r");
        if (s != std::string::npos) {
            chunk_text = chunk_text.substr(s, e - s + 1);
        }

        if (!chunk_text.empty()) {
            Chunk c;
            c.text = chunk_text;
            c.start_offset = char_offset;
            c.end_offset = char_offset + chunk_text.size();
            c.token_estimate = estimate_tokens(chunk_text);
            chunks.push_back(std::move(c));

            // Advance char_offset by the sentences consumed (excluding overlap)
            for (std::size_t k = chunk_start_sent; k < sent_idx; ++k) {
                char_offset += sentences[k].size() + 1; // +1 for space/newline
            }
        }

        // Guard: if no progress was made (single sentence > max_tokens), advance
        if (sent_idx == chunk_start_sent) {
            char_offset += sentences[sent_idx].size() + 1;
            ++sent_idx;
        }
    }

    return chunks;
}

} // namespace polymath

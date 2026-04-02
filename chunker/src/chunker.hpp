#pragma once

#include <string>
#include <vector>
#include <cstddef>

namespace polymath {

struct Chunk {
    std::string text;
    std::size_t start_offset;
    std::size_t end_offset;
    std::size_t token_estimate;
};

class SemanticChunker {
public:
    explicit SemanticChunker(std::size_t max_tokens = 256,
                              std::size_t overlap_tokens = 32);

    std::vector<Chunk> chunk(const std::string& text) const;

    std::size_t max_tokens() const noexcept { return max_tokens_; }
    std::size_t overlap_tokens() const noexcept { return overlap_tokens_; }

private:
    std::size_t max_tokens_;
    std::size_t overlap_tokens_;

    std::vector<std::string> split_sentences(const std::string& text) const;
    std::size_t estimate_tokens(const std::string& text) const;
    std::string get_overlap_text(const std::vector<std::string>& sentences,
                                  std::size_t end_idx) const;
};

} // namespace polymath

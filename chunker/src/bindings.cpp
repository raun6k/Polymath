#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "chunker.hpp"

namespace py = pybind11;

PYBIND11_MODULE(fast_chunker, m) {
    m.doc() = "High-performance semantic text chunker for Polymath";

    py::class_<polymath::Chunk>(m, "Chunk")
        .def(py::init<>())
        .def_readwrite("text", &polymath::Chunk::text)
        .def_readwrite("start_offset", &polymath::Chunk::start_offset)
        .def_readwrite("end_offset", &polymath::Chunk::end_offset)
        .def_readwrite("token_estimate", &polymath::Chunk::token_estimate)
        .def("__repr__", [](const polymath::Chunk& c) {
            return "<Chunk start=" + std::to_string(c.start_offset) +
                   " end=" + std::to_string(c.end_offset) +
                   " tokens=" + std::to_string(c.token_estimate) + ">";
        });

    py::class_<polymath::SemanticChunker>(m, "SemanticChunker")
        .def(py::init<std::size_t, std::size_t>(),
             py::arg("max_tokens") = 256,
             py::arg("overlap_tokens") = 32)
        .def("chunk", &polymath::SemanticChunker::chunk,
             py::arg("text"),
             "Split text into semantically meaningful chunks")
        .def_property_readonly("max_tokens",
             &polymath::SemanticChunker::max_tokens)
        .def_property_readonly("overlap_tokens",
             &polymath::SemanticChunker::overlap_tokens)
        .def("__repr__", [](const polymath::SemanticChunker& sc) {
            return "<SemanticChunker max_tokens=" +
                   std::to_string(sc.max_tokens()) +
                   " overlap_tokens=" +
                   std::to_string(sc.overlap_tokens()) + ">";
        });
}

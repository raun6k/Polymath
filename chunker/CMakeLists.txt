cmake_minimum_required(VERSION 3.15)
project(polymath_chunker VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Release build by default
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")

# ── pybind11 extension ──────────────────────────────────────────────────────
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

# Try to find pybind11 via cmake; fall back to python -m pybind11 --cmakedir
find_package(pybind11 CONFIG QUIET)
if(NOT pybind11_FOUND)
  execute_process(
    COMMAND "${Python3_EXECUTABLE}" -m pybind11 --cmakedir
    OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
  find_package(pybind11 CONFIG REQUIRED PATHS "${PYBIND11_CMAKE_DIR}")
endif()

pybind11_add_module(fast_chunker
  src/chunker.cpp
  src/bindings.cpp
)

target_include_directories(fast_chunker PRIVATE src)

# Install the .so next to the project root so Python can import it
install(TARGETS fast_chunker DESTINATION "${CMAKE_SOURCE_DIR}/..")

# ── standalone C++ tests ────────────────────────────────────────────────────
option(BUILD_TESTS "Build C++ unit tests" ON)

if(BUILD_TESTS)
  enable_testing()

  # Header-only GoogleTest via FetchContent
  include(FetchContent)
  FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG        v1.14.0
  )
  set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(googletest)

  add_executable(test_chunker
    tests/test_chunker.cpp
    src/chunker.cpp
  )
  target_include_directories(test_chunker PRIVATE src)
  target_link_libraries(test_chunker PRIVATE GTest::gtest_main)
  target_compile_features(test_chunker PRIVATE cxx_std_17)

  include(GoogleTest)
  gtest_discover_tests(test_chunker)
endif()

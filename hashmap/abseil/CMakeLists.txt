cmake_minimum_required(VERSION 3.16)
project(hashbench_absl LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Ensure Release build by default
if (NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

find_package(absl CONFIG REQUIRED)

# The logical target name is hashbench_absl, but the output binary will be named 'hashbench'
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
add_executable(hashbench_absl benchmark.cc)
set_target_properties(hashbench_absl PROPERTIES OUTPUT_NAME hashbench)

target_link_libraries(hashbench_absl PRIVATE absl::flat_hash_map absl::strings)

# Build optimizations
if (CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(hashbench_absl PRIVATE -O3 -march=native)
elseif (MSVC)
  target_compile_options(hashbench_absl PRIVATE /O2)
endif()


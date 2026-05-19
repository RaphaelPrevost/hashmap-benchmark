cmake_minimum_required(VERSION 3.16)
project(hashbench_folly LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if (NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

find_package(gflags CONFIG REQUIRED)

# Folly may refer to an un-namespaced target/library called gflags_shared.
# Bridge it to the target exported by your gflags package.
if (NOT TARGET gflags_shared)
  add_library(gflags_shared INTERFACE IMPORTED)

  if (TARGET gflags::gflags_shared)
    set_target_properties(gflags_shared PROPERTIES
      INTERFACE_LINK_LIBRARIES gflags::gflags_shared)
  elseif (TARGET gflags::gflags)
    set_target_properties(gflags_shared PROPERTIES
      INTERFACE_LINK_LIBRARIES gflags::gflags)
  else()
    message(FATAL_ERROR "Found gflags, but no usable gflags CMake target")
  endif()
endif()

find_package(folly CONFIG REQUIRED)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
add_executable(hashbench_folly benchmark.cc)
set_target_properties(hashbench_folly PROPERTIES OUTPUT_NAME hashbench)

target_link_libraries(hashbench_folly PRIVATE Folly::folly)

if (CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(hashbench_folly PRIVATE -O3 -march=native)
elseif (MSVC)
  target_compile_options(hashbench_folly PRIVATE /O2)
endif()

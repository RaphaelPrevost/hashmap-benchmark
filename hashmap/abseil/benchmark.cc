#include "absl/container/flat_hash_map.h"
#include "absl/strings/string_view.h"
#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#define KEY_PREFIX_MISS 'B'

// Mode parsing
bool is_mode(const char* arg, const char* mode) { return std::strcmp(arg, mode) == 0; }

int main(int argc, char** argv) {
    if (argc != 3) {
        std::fprintf(stderr, "Usage: %s <insert|update|retrieve|miss> <count>\n", argv[0]);
        return EXIT_FAILURE;
    }

    const char* mode = argv[1];
    uintptr_t count = std::strtoull(argv[2], nullptr, 10);
    char key[BUFSIZ];
    std::size_t len = 0;

    using Key = std::string;
    using Value = uintptr_t;
    absl::flat_hash_map<Key, Value> h;
    //h.reserve(count);

    // 1. Insert phase (All modes start by populating)
    for (uintptr_t i = 1; i <= count; ++i) {
        int n = std::snprintf(key, sizeof(key), "%" PRIuPTR, i);
        if (n < 0 || static_cast<std::size_t>(n) >= sizeof(key)) {
            std::fprintf(stderr, "(!) snprintf failed for %" PRIuPTR "\n", i);
            return EXIT_FAILURE;
        }
        len = static_cast<std::size_t>(n);
        h.emplace(Key(key, len), i);
    }

    if (is_mode(mode, "insert")) return EXIT_SUCCESS;

    // 2. Update phase
    if (is_mode(mode, "update")) {
        for (uintptr_t i = 1; i <= count; ++i) {
            int n = std::snprintf(key, sizeof(key), "%" PRIuPTR, i);
            if (n < 0 || static_cast<std::size_t>(n) >= sizeof(key)) {
                std::fprintf(stderr, "(!) snprintf failed for %" PRIuPTR "\n", i);
                return EXIT_FAILURE;
            }
            len = static_cast<std::size_t>(n);
            h[Key(key, len)] = (i + 1);
        }
        return EXIT_SUCCESS;
    }

    // 3. Retrieve phase
    if (is_mode(mode, "retrieve")) {
        for (uintptr_t i = 1; i <= count; ++i) {
            int n = std::snprintf(key, sizeof(key), "%" PRIuPTR, i);
            if (n < 0 || static_cast<std::size_t>(n) >= sizeof(key)) {
                std::fprintf(stderr, "(!) snprintf failed for %" PRIuPTR "\n", i);
                return EXIT_FAILURE;
            }
            len = static_cast<std::size_t>(n);
            auto it = h.find(Key(key, len));
            if (it == h.end() || it->second != i) return EXIT_FAILURE;
        }
        return EXIT_SUCCESS;
    }

    // 4. Miss phase
    if (is_mode(mode, "miss")) {
        for (uintptr_t i = 1; i <= count; ++i) {
            int n = std::snprintf(key, sizeof(key), "%c%" PRIuPTR, KEY_PREFIX_MISS, i);
            if (n < 0 || static_cast<std::size_t>(n) >= sizeof(key)) {
                std::fprintf(stderr, "(!) snprintf failed for %" PRIuPTR "\n", i);
                return EXIT_FAILURE;
            }
            len = static_cast<std::size_t>(n);
            if (h.contains(Key(key, len))) return EXIT_FAILURE;
        }
        return EXIT_SUCCESS;
    }

    return EXIT_FAILURE;
}


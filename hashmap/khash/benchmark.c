#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "src/khash.h"

#define KEY_PREFIX_MISS 'B'

KHASH_MAP_INIT_STR(str, uintptr_t)

static void
usage(const char *prog)
{
    fprintf(stderr, "Usage: %s <insert|update|retrieve|miss> <count>\n", prog);
}

static int
parse_count(const char *arg, uintptr_t *out)
{
    char *end = NULL;
    unsigned long long value;

    errno = 0;
    value = strtoull(arg, &end, 10);
    if (errno != 0 || end == arg || *end != '\0' || value == 0) {
        return -1;
    }

    *out = (uintptr_t) value;
    return 0;
}

static void
free_all_keys(khash_t(str) *h)
{
    khint_t k;
    for (k = kh_begin(h); k != kh_end(h); ++k) {
        if (kh_exist(h, k)) {
            free((char *) kh_key(h, k));
        }
    }
}

int
main(int argc, char **argv)
{
    khash_t(str) *h = NULL;
    khint_t k;
    uintptr_t count = 0, i = 0, got = 0;
    size_t len = 0;
    int missing = 0;
    int ret = 0;
    char key[BUFSIZ];
    char *dup = NULL;
    const char *mode = NULL;

    if (argc != 3) {
        usage(argv[0]);
        return EXIT_FAILURE;
    }

    mode = argv[1];
    if (
        strcmp(mode, "insert")   != 0 &&
        strcmp(mode, "update")   != 0 &&
        strcmp(mode, "retrieve") != 0 &&
        strcmp(mode, "miss")     != 0
    ) {
        usage(argv[0]);
        return EXIT_FAILURE;
    }

    if (parse_count(argv[2], &count) != 0) {
        fprintf(stderr, "(!) Invalid count: %s\n", argv[2]);
        return EXIT_FAILURE;
    }

    h = kh_init(str);
    if (!h) {
        fprintf(stderr, "(!) Failed to allocate khash\n");
        return EXIT_FAILURE;
    }

    /* insert phase: always needed */
    for (i = 1; i <= count; ++i) {
        len = snprintf(key, sizeof(key), "%" PRIuPTR, i);
        dup = strdup(key);
        if (!dup) {
            fprintf(stderr, "(!) strdup failed\n");
            free_all_keys(h);
            kh_destroy(str, h);
            return EXIT_FAILURE;
        }

        k = kh_put(str, h, dup, &ret);
        if (ret < 0) {
            fprintf(stderr, "(!) kh_put failed\n");
            free(dup);
            free_all_keys(h);
            kh_destroy(str, h);
            return EXIT_FAILURE;
        }

        if (ret == 0) {
            /* key already existed; should not happen here */
            free(dup);
        }

        kh_value(h, k) = i;
    }

    if (strcmp(mode, "insert") == 0) {
        free_all_keys(h);
        kh_destroy(str, h);
        return EXIT_SUCCESS;
    }

    if (strcmp(mode, "update") == 0) {
        for (i = 1; i <= count; ++i) {
            len = snprintf(key, sizeof(key), "%" PRIuPTR, i);
            k = kh_get(str, h, key);
            if (k == kh_end(h)) {
                missing ++;
                fprintf(stderr, "(!) Key %s is missing during update\n", key);
                continue;
            }
            kh_value(h, k) = i + 1;
        }

        free_all_keys(h);
        kh_destroy(str, h);
        return (missing == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    if (strcmp(mode, "retrieve") == 0) {
        for (i = 1; i <= count; ++i) {
            len = snprintf(key, sizeof(key), "%" PRIuPTR, i);
            k = kh_get(str, h, key);
            if (k == kh_end(h)) {
                missing ++;
                fprintf(stderr, "(!) Key %s is missing\n", key);
                continue;
            }

            got = kh_value(h, k);
            if (got != i) {
                missing ++;
            }
        }

        free_all_keys(h);
        kh_destroy(str, h);
        return (missing == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    if (strcmp(mode, "miss") == 0) {
        for (i = 1; i <= count; ++i) {
            len = snprintf(key, sizeof(key), "%c%" PRIuPTR, KEY_PREFIX_MISS, i);
            k = kh_get(str, h, key);
            if (k != kh_end(h)) {
                missing ++;
                fprintf(stderr, "(!) Missing key %s unexpectedly found\n", key);
            }
        }

        free_all_keys(h);
        kh_destroy(str, h);
        return (missing == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    free_all_keys(h);
    kh_destroy(str, h);
    return EXIT_FAILURE;
}


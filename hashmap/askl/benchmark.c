#include "src/lib/askl_htable.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define KEY_PREFIX_MISS 'B'

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

int
main(int argc, char **argv)
{
    Map *h = NULL;
    Variant val = { 0 };
    uintptr_t count = 0, i = 0, got = 0;
    size_t len = 0;
    int missing = 0;
    char key[BUFSIZ];
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

    if (parse_count(argv[2], & count) != 0) {
        fprintf(stderr, "(!) Invalid count: %s\n", argv[2]);
        return EXIT_FAILURE;
    }

    if (! (h = map_alloc(NULL))) {
        fprintf(stderr, "(!) Allocating hash table: FAILURE\n");
        return EXIT_FAILURE;
    }

    //map_reserve(h, count);

    /* insert phase: always needed */
    for (i = 1; i <= count; i ++) {
        len = snprintf(key, sizeof(key), "%" PRIuPTR, i);
        map_insert(h, key, len, variant_from_integer(i));
    }

    if (strcmp(mode, "insert") == 0) {
        h = map_free(h);
        return EXIT_SUCCESS;
    }

    /* update phase */
    if (strcmp(mode, "update") == 0) {
        for (i = 1; i <= count; i ++) {
            len = snprintf(key, sizeof(key), "%" PRIuPTR, i);
            map_update(h, key, len, variant_from_integer(i + 1));
        }

        h = map_free(h);
        return EXIT_SUCCESS;
    }

    /* retrieve phase */
    if (strcmp(mode, "retrieve") == 0) {
        for (i = 1; i <= count; i ++) {
            len = snprintf(key, sizeof(key), "%" PRIuPTR, i);
            val = map_get(h, key, len);

            if (is_integer(val)) {
                got = variant_to_integer(val);
                if (got != i) {
                    missing ++;
                    fprintf(stderr, "(!) Bad value for key %" PRIuPTR "\n", i);
                }
            } else {
                missing ++;
                fprintf(stderr, "(!) Key %" PRIuPTR " is missing\n", i);
            }
        }

        h = map_free(h);
        return (missing == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    /* miss phase */
    if (strcmp(mode, "miss") == 0) {
        for (i = 1; i <= count; i ++) {
            len = snprintf(key, sizeof(key), "%c%" PRIuPTR, KEY_PREFIX_MISS, i);
            val = map_get(h, key, len);

            if (is_integer(val)) {
                missing ++;
                got = variant_to_integer(val);
            }
        }

        h = map_free(h);
        return (missing == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    h = map_free(h);
    return EXIT_FAILURE;
}


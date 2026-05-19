#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <inttypes.h>

/* M*LIB string oplist with hash/equal/init/clear/set */
#include "src/m-string.h"
#include "src/m-dict.h"

#define KEY_PREFIX_MISS 'B'

/* Define a string->uintptr_t dictionary using M*LIB's chained (DEF2) variant */
M_DICT_DEF2(dict_str,
    m_string_t, M_STRING_OPLIST,
    uintptr_t,  M_BASIC_OPLIST)

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
    dict_str_t h;
    uintptr_t  count = 0, i = 0, got = 0;
    int        missing = 0;
    char       key[BUFSIZ];
    const char *mode = NULL;
    m_string_t mkey;

    if (argc != 3) {
        usage(argv[0]);
        return EXIT_FAILURE;
    }

    mode = argv[1];
    if (strcmp(mode, "insert")   != 0 &&
        strcmp(mode, "update")   != 0 &&
        strcmp(mode, "retrieve") != 0 &&
        strcmp(mode, "miss")     != 0) {
        usage(argv[0]);
        return EXIT_FAILURE;
    }

    if (parse_count(argv[2], &count) != 0) {
        fprintf(stderr, "(!) Invalid count: %s\n", argv[2]);
        return EXIT_FAILURE;
    }

    dict_str_init(h);
    m_string_init(mkey);

    /* insert phase: always needed */
    for (i = 1; i <= count; ++i) {
        snprintf(key, sizeof(key), "%" PRIuPTR, i);
        m_string_set_cstr(mkey, key);
        dict_str_set_at(h, mkey, i);
    }

    if (strcmp(mode, "insert") == 0) {
        m_string_clear(mkey);
        dict_str_clear(h);
        return EXIT_SUCCESS;
    }

    if (strcmp(mode, "update") == 0) {
        for (i = 1; i <= count; ++i) {
            snprintf(key, sizeof(key), "%" PRIuPTR, i);
            m_string_set_cstr(mkey, key);
            uintptr_t *val = dict_str_get(h, mkey);
            if (val == NULL) {
                missing++;
                fprintf(stderr, "(!) Key %s is missing during update\n", key);
                continue;
            }
            *val = i + 1;
        }
        m_string_clear(mkey);
        dict_str_clear(h);
        return (missing == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    if (strcmp(mode, "retrieve") == 0) {
        for (i = 1; i <= count; ++i) {
            snprintf(key, sizeof(key), "%" PRIuPTR, i);
            m_string_set_cstr(mkey, key);
            uintptr_t *val = dict_str_get(h, mkey);
            if (val == NULL) {
                missing++;
                fprintf(stderr, "(!) Key %s is missing\n", key);
                continue;
            }
            got = *val;
            if (got != i) {
                missing++;
            }
        }
        m_string_clear(mkey);
        dict_str_clear(h);
        return (missing == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    if (strcmp(mode, "miss") == 0) {
        for (i = 1; i <= count; ++i) {
            snprintf(key, sizeof(key), "%c%" PRIuPTR, KEY_PREFIX_MISS, i);
            m_string_set_cstr(mkey, key);
            uintptr_t *val = dict_str_get(h, mkey);
            if (val != NULL) {
                missing++;
                fprintf(stderr, "(!) Missing key %s unexpectedly found\n", key);
            }
        }
        m_string_clear(mkey);
        dict_str_clear(h);
        return (missing == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    m_string_clear(mkey);
    dict_str_clear(h);
    return EXIT_FAILURE;
}


#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NAME    str_map
#define KEY_TY  char *
#define VAL_TY  uintptr_t
#define HASH_TY vt_hash_string
#define CMPR_TY vt_cmpr_string
#include "src/verstable.h"

#define KEY_PREFIX_MISS 'B'

static void
usage( const char *prog )
{
    fprintf( stderr, "Usage: %s <insert|update|retrieve|miss> <count>\n", prog );
}

static int
parse_count( const char *arg, uintptr_t *out )
{
    char *end = NULL;
    unsigned long long v;
    errno = 0;
    v = strtoull( arg, &end, 10 );
    if ( errno != 0 || end == arg || *end != '\0' || v == 0 )
        return -1;
    *out = (uintptr_t) v;
    return 0;
}

static void
free_keys( str_map *h )
{
    for ( str_map_itr it = str_map_first( h );
          !str_map_is_end( it );
          it = str_map_next( it ) )
        free( it.data->key );
}

int
main( int argc, char **argv )
{
    str_map    h;
    str_map_itr it;
    uintptr_t   count = 0, i = 0, got = 0;
    int         missing = 0;
    char        key[BUFSIZ];
    char       *dup = NULL;
    const char *mode = NULL;

    if ( argc != 3 ) { usage( argv[0] ); return EXIT_FAILURE; }

    mode = argv[1];
    if ( strcmp( mode, "insert"   ) != 0 &&
         strcmp( mode, "update"   ) != 0 &&
         strcmp( mode, "retrieve" ) != 0 &&
         strcmp( mode, "miss"     ) != 0 )
    { usage( argv[0] ); return EXIT_FAILURE; }

    if ( parse_count( argv[2], &count ) != 0 ) {
        fprintf( stderr, "(!) Invalid count: %s\n", argv[2] );
        return EXIT_FAILURE;
    }

    str_map_init( &h );

    for ( i = 1; i <= count; ++i ) {
        snprintf( key, sizeof key, "%" PRIuPTR, i );
        dup = strdup( key );
        if ( !dup ) {
            fprintf( stderr, "(!) strdup failed\n" );
            free_keys( &h ); str_map_cleanup( &h );
            return EXIT_FAILURE;
        }
        it = str_map_insert( &h, dup, i );
        if ( str_map_is_end( it ) ) {
            fprintf( stderr, "(!) insert failed\n" );
            free( dup ); free_keys( &h ); str_map_cleanup( &h );
            return EXIT_FAILURE;
        }
    }

    if ( strcmp( mode, "insert" ) == 0 ) {
        free_keys( &h ); str_map_cleanup( &h );
        return EXIT_SUCCESS;
    }

    if ( strcmp( mode, "update" ) == 0 ) {
        for ( i = 1; i <= count; ++i ) {
            snprintf( key, sizeof key, "%" PRIuPTR, i );
            it = str_map_get( &h, key );
            if ( str_map_is_end( it ) ) {
                ++missing;
                fprintf( stderr, "(!) Key %s missing during update\n", key );
                continue;
            }
            it.data->val = i + 1;
        }
        free_keys( &h ); str_map_cleanup( &h );
        return ( missing == 0 ) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    if ( strcmp( mode, "retrieve" ) == 0 ) {
        for ( i = 1; i <= count; ++i ) {
            snprintf( key, sizeof key, "%" PRIuPTR, i );
            it = str_map_get( &h, key );
            if ( str_map_is_end( it ) ) { ++missing; continue; }
            got = it.data->val;
            if ( got != i ) ++missing;
        }
        free_keys( &h ); str_map_cleanup( &h );
        return ( missing == 0 ) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    if ( strcmp( mode, "miss" ) == 0 ) {
        for ( i = 1; i <= count; ++i ) {
            snprintf( key, sizeof key, "%c%" PRIuPTR, KEY_PREFIX_MISS, i );
            it = str_map_get( &h, key );
            if ( !str_map_is_end( it ) ) {
                ++missing;
                fprintf( stderr, "(!) Key %s unexpectedly found\n", key );
            }
        }
        free_keys( &h ); str_map_cleanup( &h );
        return ( missing == 0 ) ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    free_keys( &h ); str_map_cleanup( &h );
    return EXIT_FAILURE;
}


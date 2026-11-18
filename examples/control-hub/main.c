#include "hub.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (hub_initialize() != 0 || argc < 2) {
        return 1;
    }
    if (strcmp(argv[1], "serve") == 0) {
        puts("ready");
        fflush(stdout);
        for (;;) {
            pause();
        }
    }
    if (strcmp(argv[1], "resources") == 0) {
        for (size_t index = 0; index < hub_resource_count(); index++) {
            puts(hub_resource(index));
        }
        return 0;
    }
    if (strcmp(argv[1], "dispatch") == 0 && argc == 3) {
        printf("%d\n", hub_dispatch(argv[2]));
        return 0;
    }
    return 2;
}

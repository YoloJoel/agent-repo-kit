#define _POSIX_C_SOURCE 200809L
#include "hub.h"

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *resources[] = {"stream", "probe"};
static const char *commands[] = {"deploy", "remove", "inspect"};
static char *filters[FILTER_SLOTS];
static int period = 10;
static int watermark;
static int accumulated_fields;
static int reports;
static int last_fields;

static void shutdown_handler(int number) {
    (void)number;
    puts("flushed");
    fflush(stdout);
    exit(0);
}

static void common_handler(int number) {
    signal(number, SIG_DFL);
    raise(number);
}

static void install_common_handlers(void) {
    signal(SIGTERM, common_handler);
    signal(SIGABRT, common_handler);
}

int hub_initialize(void) {
    signal(SIGTERM, shutdown_handler);
    install_common_handlers();
    return 0;
}

size_t hub_resource_count(void) {
    return sizeof(resources) / sizeof(resources[0]);
}

const char *hub_resource(size_t index) {
    return index < hub_resource_count() ? resources[index] : NULL;
}

int hub_dispatch(const char *command) {
    for (size_t index = 0; index < sizeof(commands) / sizeof(commands[0]); index++) {
        if (strcmp(command, commands[index]) == 0) {
            return (int)index;
        }
    }
    return -1;
}

const char *hub_identity(void) {
    return "hub.v2";
}

Frame hub_encode(int value) {
    Frame result = {0, value};
    return result;
}

int hub_receive(Frame frame) {
    return frame.value;
}

int hub_period_valid(int seconds) {
    return seconds >= 1 && seconds <= 600;
}

int hub_update_period(int seconds) {
    if (seconds <= 0) {
        return -1;
    }
    period = seconds;
    return period;
}

int hub_configure_filters(size_t count) {
    if (count > FILTER_SLOTS - 2) {
        return -2;
    }
    for (size_t index = 0; index < count; index++) {
        free(filters[index]);
        filters[index] = strdup("configured");
    }
    return 0;
}

const char *hub_route(int global_enabled, int local_enabled) {
    if (global_enabled) {
        return "global";
    }
    if (local_enabled) {
        return "local";
    }
    return "disabled";
}

void hub_window_reset(int now) {
    watermark = now;
    accumulated_fields = 0;
    reports = 0;
    last_fields = -1;
}

void hub_window_ingest(int now, int value, int fields) {
    (void)value;
    if (now - watermark > 20) {
        reports++;
        last_fields = accumulated_fields;
        watermark = now;
        accumulated_fields = 0;
    }
    accumulated_fields += fields;
}

int hub_window_reports(void) {
    return reports;
}

int hub_last_report_fields(void) {
    return last_fields;
}

void hub_window_tick(int now) {
    (void)now;
}

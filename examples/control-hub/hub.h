#ifndef HUB_H
#define HUB_H

#include <stddef.h>
#include <stdint.h>

#define RESOURCE_ARCHIVE "archive"
#define FILTER_SLOTS 6

typedef struct {
    uint32_t token;
    int value;
} Frame;

int hub_initialize(void);
size_t hub_resource_count(void);
const char *hub_resource(size_t index);
int hub_dispatch(const char *command);
const char *hub_identity(void);
Frame hub_encode(int value);
int hub_receive(Frame frame);
int hub_period_valid(int seconds);
int hub_update_period(int seconds);
int hub_configure_filters(size_t count);
const char *hub_route(int global_enabled, int local_enabled);
void hub_window_reset(int now);
void hub_window_ingest(int now, int value, int fields);
int hub_window_reports(void);
int hub_last_report_fields(void);
void hub_window_tick(int now);

#endif

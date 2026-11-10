#pragma once
#include <stdint.h>
typedef struct { uint8_t armed, door, alarm; } security_snapshot_t;
security_snapshot_t security_snapshot(void);
void security_command(uint8_t cmd);
void security_notify(void);
void security_start(void);

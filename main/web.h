#pragma once

#include <stdbool.h>

void web_start(void);

/* True when no control frame arrived within FAILSAFE_MS. */
bool web_link_lost(void);

/* Drop the drive permission; the motor stays stopped until the next arm. */
void web_disarm(void);

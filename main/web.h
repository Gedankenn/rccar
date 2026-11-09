#pragma once

#include <stdbool.h>

void web_start(void);

/* True when no control frame arrived within FAILSAFE_MS. */
bool web_link_lost(void);

/* Drop the drive permission; the motor stays stopped until the next arm. */
void web_disarm(void);

/* Latch the drive off (low battery); only a reboot clears it. */
void web_lock(void);

/* True once the low-voltage latch fired. */
bool web_locked(void);

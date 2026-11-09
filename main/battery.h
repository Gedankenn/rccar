#pragma once

void battery_init(void);

/* Pack voltage after the divider, in volts. 0.0 if not sampled yet. */
float battery_read(void);

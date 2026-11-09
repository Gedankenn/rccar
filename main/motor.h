#pragma once

void motor_init(void);

/* duty in [-1.0, 1.0]; sign sets direction, 0 coasts. */
void motor_set(float duty);

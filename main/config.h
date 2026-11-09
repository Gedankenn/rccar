#pragma once

/*
 * Pin map for ESP32-C3 SuperMini.
 *
 * GPIO 2 / 8 / 9 are strapping pins, GPIO 11-17 are flash, GPIO 18/19 are
 * USB D-/D+, GPIO 20/21 are UART0. GPIO 4-7 double as the JTAG pins: using
 * them for PWM/I2C costs hardware debugging, not functionality.
 */
#define PIN_MOTOR_IN1      3
#define PIN_MOTOR_IN2      4
#define PIN_SERVO          5
#define PIN_VBAT_ADC       0   /* ADC1 channel 0 */
#define PIN_STATUS_LED     8   /* onboard LED, active low */
#define PIN_I2C_SDA        6   /* reserved for an IMU, not used yet */
#define PIN_I2C_SCL        7

/* Brushed-motor PWM (H-bridge IN1/IN2). */
#define MOTOR_PWM_HZ       20000
#define MOTOR_PWM_RES      LEDC_TIMER_10_BIT
#define MOTOR_MAX_DUTY     1023

/* Steering servo, 50 Hz hobby PWM. */
#define SERVO_PWM_HZ       50
#define SERVO_PWM_RES      LEDC_TIMER_14_BIT
#define SERVO_MIN_US       1000
#define SERVO_CENTER_US    1500
#define SERVO_MAX_US       2000
#define SERVO_TRIM_US      0

/* Battery divider: 100k top / 47k bottom, full scale ~3.15 V per cell. */
#define VBAT_R_TOP_KOHM    100.0f
#define VBAT_R_BOTTOM_KOHM 47.0f
#define VBAT_DIVIDER       ((VBAT_R_TOP_KOHM + VBAT_R_BOTTOM_KOHM) / VBAT_R_BOTTOM_KOHM)

/* Stop the motor if no command arrives for this long. */
#define FAILSAFE_MS        400

#define AP_SSID_PREFIX     "rccar"
#define AP_PASS            "rccar1234"

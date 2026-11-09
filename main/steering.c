#include "steering.h"

#include <stdint.h>

#include "config.h"
#include "driver/ledc.h"
#include "esp_check.h"
#include "esp_log.h"

static const char *TAG = "steering";

#define CH_SERVO LEDC_CHANNEL_2
#define PERIOD_US (1000000 / SERVO_PWM_HZ)

void steering_init(void)
{
    ledc_timer_config_t timer = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = SERVO_PWM_RES,
        .timer_num = LEDC_TIMER_1,
        .freq_hz = SERVO_PWM_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer));

    ledc_channel_config_t ch = {
        .gpio_num = PIN_SERVO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = CH_SERVO,
        .intr_type = LEDC_INTR_DISABLE,
        .timer_sel = LEDC_TIMER_1,
        .duty = 0,
        .hpoint = 0,
    };
    ESP_ERROR_CHECK(ledc_channel_config(&ch));

    steering_set(0.0f);
    ESP_LOGI(TAG, "ready (GPIO %d, %d..%d us)", PIN_SERVO, SERVO_MIN_US, SERVO_MAX_US);
}

void steering_set(float position)
{
    if (position > 1.0f) {
        position = 1.0f;
    } else if (position < -1.0f) {
        position = -1.0f;
    }

    /* Map [-1, 1] onto [min, max] around the configured center. */
    float half = (SERVO_MAX_US - SERVO_MIN_US) / 2.0f;
    float center = SERVO_CENTER_US + SERVO_TRIM_US;
    int pulse_us = (int)(center + position * half + 0.5f);

    if (pulse_us < SERVO_MIN_US) {
        pulse_us = SERVO_MIN_US;
    } else if (pulse_us > SERVO_MAX_US) {
        pulse_us = SERVO_MAX_US;
    }

    uint32_t duty = (uint32_t)((uint64_t)pulse_us * (1u << 14) / PERIOD_US);
    ESP_ERROR_CHECK(ledc_set_duty(LEDC_LOW_SPEED_MODE, CH_SERVO, duty));
    ESP_ERROR_CHECK(ledc_update_duty(LEDC_LOW_SPEED_MODE, CH_SERVO));
}

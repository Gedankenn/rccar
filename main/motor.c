#include "motor.h"

#include <stdint.h>

#include "config.h"
#include "driver/ledc.h"
#include "esp_check.h"
#include "esp_log.h"

static const char *TAG = "motor";

#define CH_IN1 LEDC_CHANNEL_0
#define CH_IN2 LEDC_CHANNEL_1

static void set_duty(ledc_channel_t ch, uint32_t duty)
{
    ESP_ERROR_CHECK(ledc_set_duty(LEDC_LOW_SPEED_MODE, ch, duty));
    ESP_ERROR_CHECK(ledc_update_duty(LEDC_LOW_SPEED_MODE, ch));
}

static void channel_init(int gpio, ledc_channel_t ch)
{
    ledc_channel_config_t cfg = {
        .gpio_num = gpio,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = ch,
        .intr_type = LEDC_INTR_DISABLE,
        .timer_sel = LEDC_TIMER_0,
        .duty = 0,
        .hpoint = 0,
    };
    ESP_ERROR_CHECK(ledc_channel_config(&cfg));
}

void motor_init(void)
{
    ledc_timer_config_t timer = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = MOTOR_PWM_RES,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = MOTOR_PWM_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer));

    channel_init(PIN_MOTOR_IN1, CH_IN1);
    channel_init(PIN_MOTOR_IN2, CH_IN2);
    motor_set(0.0f);
    ESP_LOGI(TAG, "ready (IN1=%d IN2=%d, %d Hz)", PIN_MOTOR_IN1, PIN_MOTOR_IN2, MOTOR_PWM_HZ);
}

void motor_set(float duty)
{
    if (duty > 1.0f) {
        duty = 1.0f;
    } else if (duty < -1.0f) {
        duty = -1.0f;
    }

    /* Sign-magnitude drive: one leg PWM, other leg low, both low coasts. */
    float magnitude = duty < 0.0f ? -duty : duty;
    uint32_t pwm = (uint32_t)(magnitude * MOTOR_MAX_DUTY + 0.5f);

    if (duty > 0.0f) {
        set_duty(CH_IN1, pwm);
        set_duty(CH_IN2, 0);
    } else if (duty < 0.0f) {
        set_duty(CH_IN1, 0);
        set_duty(CH_IN2, pwm);
    } else {
        set_duty(CH_IN1, 0);
        set_duty(CH_IN2, 0);
    }
}

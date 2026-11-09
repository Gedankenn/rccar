#include <stdbool.h>

#include "battery.h"
#include "config.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "motor.h"
#include "nvs_flash.h"
#include "steering.h"
#include "web.h"

static const char *TAG = "rccar";
static volatile bool s_linked;

static void failsafe_task(void *arg)
{
    (void)arg;
    while (true) {
        if (web_link_lost()) {
            if (s_linked) {
                ESP_LOGW(TAG, "link lost, disarming");
                web_disarm();
                motor_set(0.0f);
                steering_set(0.0f);
                s_linked = false;
            }
        } else {
            s_linked = true;
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

static void led_task(void *arg)
{
    (void)arg;
    gpio_reset_pin(PIN_STATUS_LED);
    gpio_set_direction(PIN_STATUS_LED, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_STATUS_LED, 1); /* active low: off */

    bool phase = false;
    while (true) {
        int delay_ms = 500;
        if (web_locked()) {
            delay_ms = 100; /* fast blink: drive latched off */
            phase = !phase;
            gpio_set_level(PIN_STATUS_LED, phase ? 0 : 1);
        } else if (s_linked) {
            gpio_set_level(PIN_STATUS_LED, 0); /* solid while a client drives */
            phase = false;
        } else {
            phase = !phase;
            gpio_set_level(PIN_STATUS_LED, phase ? 0 : 1); /* idle blink */
        }
        vTaskDelay(pdMS_TO_TICKS(delay_ms));
    }
}

static void battery_task(void *arg)
{
    (void)arg;
    int low_samples = 0;
    while (true) {
        float volts = battery_read();
        if (volts > 0.5f && volts < VBAT_CUTOFF_V) {
            if (++low_samples >= VBAT_CUTOFF_COUNT) {
                ESP_LOGE(TAG, "pack at %.2f V, locking drive", volts);
                web_lock();
                motor_set(0.0f);
                low_samples = 0;
            }
        } else {
            low_samples = 0;
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void app_main(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    battery_init();
    motor_init();
    steering_init();
    web_start();

    /* Park the steering before the first client arrives. */
    motor_set(0.0f);
    steering_set(0.0f);

    xTaskCreate(failsafe_task, "failsafe", 3072, NULL, 6, NULL);
    xTaskCreate(led_task, "led", 2048, NULL, 2, NULL);
    xTaskCreate(battery_task, "battery", 3072, NULL, 1, NULL);

    ESP_LOGI(TAG, "vbat %.2f V, free heap %lu", battery_read(),
             (unsigned long)esp_get_free_heap_size());
}

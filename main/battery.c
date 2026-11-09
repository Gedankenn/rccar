#include "battery.h"

#include "config.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"

static adc_oneshot_unit_handle_t s_adc;

void battery_init(void)
{
    adc_oneshot_unit_init_cfg_t unit = {
        .unit_id = ADC_UNIT_1,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&unit, &s_adc));

    adc_oneshot_chan_cfg_t chan = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(s_adc, ADC_CHANNEL_0, &chan));
}

float battery_read(void)
{
    int raw = 0;
    if (adc_oneshot_read(s_adc, ADC_CHANNEL_0, &raw) != ESP_OK) {
        return 0.0f;
    }
    return (raw / 4095.0f) * 3.3f * VBAT_DIVIDER;
}

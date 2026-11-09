#include "web.h"

#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "battery.h"
#include "cJSON.h"
#include "config.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "motor.h"
#include "steering.h"

extern const uint8_t index_html_start[] asm("_binary_index_html_start");
extern const uint8_t index_html_end[] asm("_binary_index_html_end");

static const char *TAG = "web";

static httpd_handle_t s_server;
static atomic_uint s_last_cmd_ms;
static atomic_bool s_armed;
static atomic_bool s_locked;
static float s_throttle;
static float s_steering;

static uint32_t now_ms(void)
{
    return (uint32_t)(esp_timer_get_time() / 1000);
}

bool web_link_lost(void)
{
    return (now_ms() - atomic_load(&s_last_cmd_ms)) > FAILSAFE_MS;
}

void web_disarm(void)
{
    atomic_store(&s_armed, false);
}

void web_lock(void)
{
    atomic_store(&s_locked, true);
    atomic_store(&s_armed, false);
}

bool web_locked(void)
{
    return atomic_load(&s_locked);
}

static float clampf(float v)
{
    return v < -1.0f ? -1.0f : (v > 1.0f ? 1.0f : v);
}

static void send_status(httpd_req_t *req)
{
    char buf[160];
    snprintf(buf, sizeof(buf),
             "{\"vbat\":%.2f,\"t\":%.2f,\"s\":%.2f,\"arm\":%d,\"lock\":%d}",
             battery_read(), s_throttle, s_steering,
             atomic_load(&s_armed) ? 1 : 0, atomic_load(&s_locked) ? 1 : 0);

    httpd_ws_frame_t frame = {
        .type = HTTPD_WS_TYPE_TEXT,
        .payload = (uint8_t *)buf,
        .len = strlen(buf),
    };
    httpd_ws_send_frame(req, &frame);
}

static void apply_command(const char *text, size_t len, httpd_req_t *req)
{
    cJSON *root = cJSON_ParseWithLength(text, len);
    if (root == NULL) {
        ESP_LOGW(TAG, "bad json");
        return;
    }

    cJSON *t = cJSON_GetObjectItemCaseSensitive(root, "t");
    cJSON *s = cJSON_GetObjectItemCaseSensitive(root, "s");
    cJSON *a = cJSON_GetObjectItemCaseSensitive(root, "a");

    if (cJSON_IsNumber(t)) {
        s_throttle = clampf((float)t->valuedouble);
    }
    if (cJSON_IsNumber(s)) {
        s_steering = clampf((float)s->valuedouble);
    }
    if (cJSON_IsBool(a) || cJSON_IsNumber(a)) {
        bool want = cJSON_IsBool(a) ? cJSON_IsTrue(a) : a->valuedouble != 0.0;
        if (atomic_load(&s_locked)) {
            want = false; /* low-voltage latch survives until reboot */
        }
        atomic_store(&s_armed, want);
        if (!want) {
            s_throttle = 0.0f;
        }
    }
    cJSON_Delete(root);

    /* Steering stays live while disarmed, the drive motor does not. */
    motor_set(atomic_load(&s_armed) ? s_throttle : 0.0f);
    steering_set(s_steering);
    atomic_store(&s_last_cmd_ms, now_ms());

    send_status(req);
}

static esp_err_t ws_handler(httpd_req_t *req)
{
    if (req->method == HTTP_GET) {
        /* Handshake. A new client starts disarmed and centered. */
        atomic_store(&s_armed, false);
        s_throttle = 0.0f;
        s_steering = 0.0f;
        motor_set(0.0f);
        steering_set(0.0f);
        atomic_store(&s_last_cmd_ms, now_ms());
        ESP_LOGI(TAG, "client connected");
        return ESP_OK;
    }

    httpd_ws_frame_t frame = {.type = HTTPD_WS_TYPE_TEXT};
    esp_err_t err = httpd_ws_recv_frame(req, &frame, 0);
    if (err != ESP_OK) {
        return err;
    }
    if (frame.type != HTTPD_WS_TYPE_TEXT || frame.len == 0 || frame.len > 256) {
        return ESP_OK;
    }

    uint8_t *buf = calloc(1, frame.len + 1);
    if (buf == NULL) {
        return ESP_ERR_NO_MEM;
    }
    frame.payload = buf;
    err = httpd_ws_recv_frame(req, &frame, frame.len);
    if (err == ESP_OK) {
        apply_command((const char *)buf, frame.len, req);
    }
    free(buf);
    return err;
}

static esp_err_t root_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    return httpd_resp_send(req, (const char *)index_html_start,
                           index_html_end - index_html_start);
}

static esp_err_t api_status_handler(httpd_req_t *req)
{
    char buf[160];
    snprintf(buf, sizeof(buf),
             "{\"vbat\":%.2f,\"t\":%.2f,\"s\":%.2f,\"arm\":%d,\"lost\":%d,\"lock\":%d}",
             battery_read(), s_throttle, s_steering,
             atomic_load(&s_armed) ? 1 : 0, web_link_lost() ? 1 : 0,
             atomic_load(&s_locked) ? 1 : 0);
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_sendstr(req, buf);
}

static void wifi_start(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));

    uint8_t mac[6] = {0};
    ESP_ERROR_CHECK(esp_wifi_get_mac(WIFI_IF_AP, mac));

    wifi_config_t ap = {0};
    snprintf((char *)ap.ap.ssid, sizeof(ap.ap.ssid), "%s-%02X%02X",
             AP_SSID_PREFIX, mac[4], mac[5]);
    ap.ap.ssid_len = (uint8_t)strlen((char *)ap.ap.ssid);
    strlcpy((char *)ap.ap.password, AP_PASS, sizeof(ap.ap.password));
    ap.ap.channel = 6;
    ap.ap.max_connection = 4;
    ap.ap.authmode = WIFI_AUTH_WPA2_PSK;
    ap.ap.pmf_cfg.required = false;

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "AP \"%s\" up, open http://192.168.4.1/", ap.ap.ssid);
}

void web_start(void)
{
    atomic_store(&s_last_cmd_ms, now_ms());
    atomic_store(&s_armed, false);
    atomic_store(&s_locked, false);

    wifi_start();

    httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
    cfg.max_open_sockets = 4;
    cfg.lru_purge_enable = true;
    cfg.stack_size = 8192;
    cfg.keep_alive_enable = true;
    ESP_ERROR_CHECK(httpd_start(&s_server, &cfg));

    httpd_uri_t root = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = root_handler,
    };
    httpd_uri_t ws = {
        .uri = "/ws",
        .method = HTTP_GET,
        .handler = ws_handler,
        .is_websocket = true,
    };
    httpd_uri_t status = {
        .uri = "/api/status",
        .method = HTTP_GET,
        .handler = api_status_handler,
    };
    ESP_ERROR_CHECK(httpd_register_uri_handler(s_server, &root));
    ESP_ERROR_CHECK(httpd_register_uri_handler(s_server, &ws));
    ESP_ERROR_CHECK(httpd_register_uri_handler(s_server, &status));

    ESP_LOGI(TAG, "http server on :80");
}

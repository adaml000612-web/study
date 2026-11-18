/*
 * SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */
/* MQTT over TLS Example

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/
#include <stdlib.h>
#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "nvs_flash.h"
#include "sdkconfig.h"

#include "protocol_examples_common.h"


#include "mqtt_client.h"

#include "freertos/event_groups.h"
#include "esp_wifi.h"
#include "mbedtls/md.h"
#include "mbedtls/base64.h"
#include "esp_sntp.h"
#include <time.h>

static const char *TAG = "mqtts_example";

#if CONFIG_EXAMPLE_BROKER_CERTIFICATE_OVERRIDDEN
static const char cert_override_pem[] =
    "-----BEGIN CERTIFICATE-----\n"
    CONFIG_EXAMPLE_BROKER_CERTIFICATE_OVERRIDE "\n"
    "-----END CERTIFICATE-----";
#endif

#if CONFIG_EXAMPLE_CERT_VALIDATE_MOSQUITTO_CA
/* Embedded Mosquitto CA certificate for test.mosquitto.org:8883 */
extern const uint8_t mosquitto_org_crt_start[] asm("_binary_mosquitto_org_crt_start");
extern const uint8_t mosquitto_org_crt_end[] asm("_binary_mosquitto_org_crt_end");
#endif

#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static EventGroupHandle_t s_wifi_event_group;
static int s_retry_num = 0;

static void wifi_event_handler(void *arg,
                               esp_event_base_t event_base,
                               int32_t event_id,
                               void *event_data)
{
    if (event_base == WIFI_EVENT &&
        event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();

    } else if (event_base == WIFI_EVENT &&
               event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_retry_num < CONFIG_EXAMPLE_WIFI_CONN_MAX_RETRY) {
            esp_wifi_connect();
            s_retry_num++;

            ESP_LOGI(TAG, "Wi-Fi retry: %d/%d",
                     s_retry_num,
                     CONFIG_EXAMPLE_WIFI_CONN_MAX_RETRY);
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
        }

    } else if (event_base == IP_EVENT &&
               event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;

        ESP_LOGI(TAG, "Wi-Fi connected! IP: " IPSTR,
                 IP2STR(&event->ip_info.ip));

        s_retry_num = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

static void wifi_init_sta(void)
{
    s_wifi_event_group = xEventGroupCreate();

    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;

    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT,
        ESP_EVENT_ANY_ID,
        &wifi_event_handler,
        NULL,
        &instance_any_id));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT,
        IP_EVENT_STA_GOT_IP,
        &wifi_event_handler,
        NULL,
        &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = CONFIG_EXAMPLE_WIFI_SSID,
            .password = CONFIG_EXAMPLE_WIFI_PASSWORD,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "wifi_init_sta finished, waiting for connection...");

    EventBits_t bits = xEventGroupWaitBits(
        s_wifi_event_group,
        WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
        pdFALSE,
        pdFALSE,
        portMAX_DELAY);

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "Wi-Fi connected successfully!");
    } else if (bits & WIFI_FAIL_BIT) {
        ESP_LOGI(TAG, "Wi-Fi connection failed!");
    }
}

/*
 * @brief Event handler registered to receive MQTT events
 *
 *  This function is called by the MQTT client event loop.
 *
 * @param handler_args user data registered to the event.
 * @param base Event base for the handler(always MQTT Base in this example).
 * @param event_id The id for the received event.
 * @param event_data The data for the event, esp_mqtt_event_handle_t.
 */
static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    ESP_LOGD(TAG, "Event dispatched from event loop base=%s, event_id=%" PRIi32, base, event_id);
    esp_mqtt_event_handle_t event = event_data;
    esp_mqtt_client_handle_t client = event->client;
    int msg_id;
    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED: {
    ESP_LOGI(TAG, "MQTT_EVENT_CONNECTED");

    char set_topic[192];
    snprintf(set_topic, sizeof(set_topic),
             "$sys/%s/%s/thing/property/set",
             CONFIG_ONENET_PRODUCT_ID,
             CONFIG_ONENET_DEVICE_NAME);

    int msg_id = esp_mqtt_client_subscribe(client, set_topic, 0);

    ESP_LOGI(TAG, "Subscribed to: %s, msg_id=%d",
             set_topic, msg_id);
    break;
}
    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "MQTT_EVENT_DISCONNECTED");
        break;

   case MQTT_EVENT_SUBSCRIBED:
    ESP_LOGI(TAG, "MQTT_EVENT_SUBSCRIBED, msg_id=%d",
             event->msg_id);
    break;
    case MQTT_EVENT_UNSUBSCRIBED:
        ESP_LOGI(TAG, "MQTT_EVENT_UNSUBSCRIBED, msg_id=%d", event->msg_id);
        break;
    case MQTT_EVENT_PUBLISHED:
        ESP_LOGI(TAG, "MQTT_EVENT_PUBLISHED, msg_id=%d", event->msg_id);
        break;
    case MQTT_EVENT_DATA:
        ESP_LOGI(TAG, "MQTT_EVENT_DATA");
        printf("TOPIC=%.*s\r\n", event->topic_len, event->topic);
        printf("DATA=%.*s\r\n", event->data_len, event->data);
        break;
    case MQTT_EVENT_ERROR:
        ESP_LOGI(TAG, "MQTT_EVENT_ERROR");
        if (event->error_handle->error_type == MQTT_ERROR_TYPE_TCP_TRANSPORT) {
            ESP_LOGI(TAG, "Last error code reported from esp-tls: 0x%x", event->error_handle->esp_tls_last_esp_err);
            ESP_LOGI(TAG, "Last tls stack error number: 0x%x", event->error_handle->esp_tls_stack_err);
            ESP_LOGI(TAG, "Last captured errno : %d (%s)", event->error_handle->esp_transport_sock_errno,
                     strerror(event->error_handle->esp_transport_sock_errno));
        } else if (event->error_handle->error_type == MQTT_ERROR_TYPE_CONNECTION_REFUSED) {
            ESP_LOGI(TAG, "Connection refused error: 0x%x", event->error_handle->connect_return_code);
        } else {
            ESP_LOGW(TAG, "Unknown error type: 0x%x", event->error_handle->error_type);
        }
        break;
    default:
        ESP_LOGI(TAG, "Other event id:%d", event->event_id);
        break;
    }
}

static char *generate_onenet_token(const char *product_id,
                                   const char *device_name,
                                   const char *device_key_b64)
{
    /* 1. Base64解码设备密钥 */
    size_t key_len = 0;

    int ret = mbedtls_base64_decode(
        NULL, 0, &key_len,
        (const unsigned char *)device_key_b64,
        strlen(device_key_b64));

    if (ret != MBEDTLS_ERR_BASE64_BUFFER_TOO_SMALL || key_len == 0) {
        ESP_LOGE(TAG, "Invalid device key");
        return NULL;
    }

    unsigned char *key = malloc(key_len);
    if (key == NULL) {
        return NULL;
    }

    ret = mbedtls_base64_decode(
        key, key_len, &key_len,
        (const unsigned char *)device_key_b64,
        strlen(device_key_b64));

    if (ret != 0) {
        free(key);
        ESP_LOGE(TAG, "Device key Base64 decode failed");
        return NULL;
    }

    /* 2. 构建设备资源路径 */
    char res[192];

    int n = snprintf(res, sizeof(res),
                     "products/%s/devices/%s",
                     product_id, device_name);

    if (n < 0 || (size_t)n >= sizeof(res)) {
        free(key);
        ESP_LOGE(TAG, "Device resource path too long");
        return NULL;
    }

    /* 3. 有效期：当前时间起24小时 */
    time_t now = time(NULL);

    if (now < (time_t)1704067200) {
        free(key);
        ESP_LOGE(TAG, "System time invalid; check NTP");
        return NULL;
    }

    char et_str[32];
    snprintf(et_str, sizeof(et_str),
             "%lld", (long long)now + 86400LL);

    const char *version = "2018-10-31";
    const char *method = "sha1";

    char sig_input[512];

    n = snprintf(sig_input, sizeof(sig_input),
                 "%s\n%s\n%s\n%s",
                 et_str, method, res, version);

    if (n < 0 || (size_t)n >= sizeof(sig_input)) {
        free(key);
        return NULL;
    }

    /* 4. 手动计算HMAC-SHA1，与PDF算法一致 */
    const mbedtls_md_info_t *md_info =
        mbedtls_md_info_from_type(MBEDTLS_MD_SHA1);

    if (md_info == NULL) {
        free(key);
        ESP_LOGE(TAG, "SHA1 is unavailable");
        return NULL;
    }

    unsigned char key_padded[64] = {0};
    unsigned char ipad[64];
    unsigned char opad[64];
    unsigned char inner[20];
    unsigned char hmac_out[20];

    if (key_len > sizeof(key_padded)) {
        ret = mbedtls_md(md_info, key, key_len, key_padded);
    } else {
        memcpy(key_padded, key, key_len);
        ret = 0;
    }

    free(key);

    if (ret != 0) {
        return NULL;
    }

    for (size_t i = 0; i < sizeof(key_padded); i++) {
        ipad[i] = key_padded[i] ^ 0x36;
        opad[i] = key_padded[i] ^ 0x5c;
    }

    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);

    ret = mbedtls_md_setup(&ctx, md_info, 0);

    if (ret == 0) {
        ret = mbedtls_md_starts(&ctx);
    }
    if (ret == 0) {
        ret = mbedtls_md_update(&ctx, ipad, sizeof(ipad));
    }
    if (ret == 0) {
        ret = mbedtls_md_update(
            &ctx,
            (const unsigned char *)sig_input,
            strlen(sig_input));
    }
    if (ret == 0) {
        ret = mbedtls_md_finish(&ctx, inner);
    }

    if (ret == 0) {
        ret = mbedtls_md_starts(&ctx);
    }
    if (ret == 0) {
        ret = mbedtls_md_update(&ctx, opad, sizeof(opad));
    }
    if (ret == 0) {
        ret = mbedtls_md_update(&ctx, inner, sizeof(inner));
    }
    if (ret == 0) {
        ret = mbedtls_md_finish(&ctx, hmac_out);
    }

    mbedtls_md_free(&ctx);

    if (ret != 0) {
        ESP_LOGE(TAG, "HMAC-SHA1 calculation failed");
        return NULL;
    }

    /* 5. Base64编码签名 */
    unsigned char sign_b64[32];
    size_t sign_len = 0;

    ret = mbedtls_base64_encode(
        sign_b64, sizeof(sign_b64), &sign_len,
        hmac_out, sizeof(hmac_out));

    if (ret != 0 || sign_len >= sizeof(sign_b64)) {
        return NULL;
    }

    sign_b64[sign_len] = '\0';

    /*
     * 6. 拼接Token并进行URL编码。
     * 空间按res最坏3倍编码长度预留。
     */
    size_t token_size =
        strlen(res) * 3 + sign_len * 3 + 160;

    char *token = malloc(token_size);
    if (token == NULL) {
        return NULL;
    }

    char *p = token;
    p += sprintf(p, "version=%s&res=", version);

    const unsigned char *s = (const unsigned char *)res;

    while (*s != '\0') {
        unsigned char c = *s++;

        if ((c >= 'a' && c <= 'z') ||
            (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') ||
            c == '-' || c == '_' || c == '.' || c == '~') {
            *p++ = (char)c;
        } else {
            p += sprintf(p, "%%%02X", (unsigned int)c);
        }
    }

    p += sprintf(p, "&et=%s&method=%s&sign=",
                 et_str, method);

    s = sign_b64;

    while (*s != '\0') {
        unsigned char c = *s++;

        if ((c >= 'a' && c <= 'z') ||
            (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') ||
            c == '-' || c == '_' || c == '.' || c == '~') {
            *p++ = (char)c;
        } else {
            p += sprintf(p, "%%%02X", (unsigned int)c);
        }
    }

    *p = '\0';
    return token;
}

static void sync_ntp_time(void)
{
    ESP_LOGI(TAG, "Syncing NTP time...");

    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, "ntp.aliyun.com");
    esp_sntp_setservername(1, "ntp1.aliyun.com");
    esp_sntp_init();

    /* 最多等待约20秒 */
    time_t now = 0;
    struct tm timeinfo = {0};
    int retry = 0;

    while (timeinfo.tm_year < (2024 - 1900) && ++retry <= 20) {
        time(&now);
        localtime_r(&now, &timeinfo);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    if (timeinfo.tm_year >= (2024 - 1900)) {
        ESP_LOGI(TAG, "NTP time synced: %lld", (long long)now);
    } else {
        ESP_LOGW(TAG, "NTP sync timeout! Token may be invalid.");
    }
}

static void sync_ntp_time(void)
{
    ESP_LOGI(TAG, "Syncing NTP time...");

    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, "ntp.aliyun.com");
    esp_sntp_setservername(1, "ntp1.aliyun.com");
    esp_sntp_init();

    /* 最多等待约20秒 */
    time_t now = 0;
    struct tm timeinfo = {0};
    int retry = 0;

    while (timeinfo.tm_year < (2024 - 1900) && ++retry <= 20) {
        time(&now);
        localtime_r(&now, &timeinfo);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    if (timeinfo.tm_year >= (2024 - 1900)) {
        ESP_LOGI(TAG, "NTP time synced: %lld", (long long)now);
    } else {
        ESP_LOGW(TAG, "NTP sync timeout! Token may be invalid.");
    }
}

static void mqtt_app_start(void)
{
    char mqtt_uri[192];

    snprintf(mqtt_uri, sizeof(mqtt_uri),
             "mqtt://%s",
             CONFIG_ONENET_BROKER_ADDRESS);

    char *token = generate_onenet_token(
        CONFIG_ONENET_PRODUCT_ID,
        CONFIG_ONENET_DEVICE_NAME,
        CONFIG_ONENET_DEVICE_KEY);

    if (token == NULL) {
        ESP_LOGE(TAG, "Failed to generate OneNet Token");
        return;
    }

    ESP_LOGI(TAG, "Token generated (len=%u)",
             (unsigned int)strlen(token));

    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = mqtt_uri,
        .credentials.username = CONFIG_ONENET_PRODUCT_ID,
        .credentials.authentication.password = token,
        .credentials.client_id = CONFIG_ONENET_DEVICE_NAME,
        .session.protocol_ver = MQTT_PROTOCOL_V_3_1_1,
        .session.keepalive = 60,
    };

    esp_mqtt_client_handle_t client =
        esp_mqtt_client_init(&mqtt_cfg);

    free(token);

    if (client == NULL) {
        ESP_LOGE(TAG, "Failed to initialize MQTT client");
        return;
    }

    ESP_ERROR_CHECK(esp_mqtt_client_register_event(
        client,
        ESP_EVENT_ANY_ID,
        mqtt_event_handler,
        NULL));

    ESP_ERROR_CHECK(esp_mqtt_client_start(client));
}

void app_main(void)
{
    ESP_LOGI(TAG, "[APP] Startup..");
    ESP_LOGI(TAG, "[APP] Free memory: %" PRIu32 " bytes", esp_get_free_heap_size());
    ESP_LOGI(TAG, "[APP] IDF version: %s", esp_get_idf_version());

    esp_log_level_set("*", ESP_LOG_INFO);
    esp_log_level_set("esp-tls", ESP_LOG_VERBOSE);
    esp_log_level_set("mqtt_client", ESP_LOG_VERBOSE);
    esp_log_level_set("mqtt_example", ESP_LOG_VERBOSE);
    esp_log_level_set("transport_base", ESP_LOG_VERBOSE);
    esp_log_level_set("transport", ESP_LOG_VERBOSE);
    esp_log_level_set("outbox", ESP_LOG_VERBOSE);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    /* This helper function configures Wi-Fi or Ethernet, as selected in menuconfig.
     * Read "Establishing Wi-Fi or Ethernet Connection" section in
     * examples/protocols/README.md for more information about this function.
     */
     wifi_init_sta();
     sync_ntp_time();

    mqtt_app_start();
}

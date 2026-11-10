/*
 * SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */
/* Includes */
#include "common.h"
#include "gap.h"
#include "nimble/nimble_npl.h"

/* Library function declarations */
void ble_store_config_init(void);

/* Private function declarations */
static void on_stack_reset(int reason);
static void on_stack_sync(void);
static void nimble_host_config_init(void);
static void nimble_host_task(void *param);

/* 按键事件：由 NimBLE Host 任务处理 */
static struct ble_npl_event lock_toggle_event;

/* 在蓝牙任务中执行状态切换和广播更新 */
static void lock_toggle_event_cb(struct ble_npl_event *event)
{
    (void)event;
    toggle_lock_status();
}

/* 用于接收按键中断通知的任务 */
static TaskHandle_t button_task_handle = NULL;

/* 中断中只发送通知，不直接更新广播 */
static void boot_button_isr(void *arg)
{
    (void)arg;

    BaseType_t task_woken = pdFALSE;
    vTaskNotifyGiveFromISR(button_task_handle, &task_woken);

    if (task_woken == pdTRUE) {
        portYIELD_FROM_ISR();
    }
}

/* 按键消抖：一次完整按下、松开，只切换一次 */
static void boot_button_task(void *arg)
{
    (void)arg;

    for (;;) {
        /* 等待按键下降沿通知 */
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        /* 暂停中断，过滤本次按键抖动 */
        gpio_intr_disable(BOOT_BUTTON_GPIO);

        vTaskDelay(pdMS_TO_TICKS(20));

        if (gpio_get_level(BOOT_BUTTON_GPIO) == 0) {
            /* 由蓝牙任务执行门锁状态切换 */
            ble_npl_eventq_put(nimble_port_get_dflt_eventq(),
                              &lock_toggle_event);
        }

        /* 等待松开，并确认高电平稳定至少 20 ms */
        for (;;) {
            while (gpio_get_level(BOOT_BUTTON_GPIO) == 0) {
                vTaskDelay(pdMS_TO_TICKS(10));
            }

            vTaskDelay(pdMS_TO_TICKS(20));

            if (gpio_get_level(BOOT_BUTTON_GPIO) == 1) {
                break;
            }
        }

        /* 清除抖动期间可能留下的通知，再恢复中断 */
        ulTaskNotifyTake(pdTRUE, 0);
        gpio_intr_enable(BOOT_BUTTON_GPIO);
    }
}

/* 初始化门锁事件、按键任务和 GPIO0 中断 */
static void boot_button_init(void)
{
    ble_npl_event_init(&lock_toggle_event,
                      lock_toggle_event_cb, NULL);

    gpio_config_t button_config = {
        .pin_bit_mask = (1ULL << BOOT_BUTTON_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&button_config));

    /* 先创建任务，确保中断触发时有任务接收通知 */
    BaseType_t result = xTaskCreate(
        boot_button_task,
        "boot_button",
        3072,
        NULL,
        4,
        &button_task_handle
    );

    if (result != pdPASS) {
        ESP_LOGE(TAG, "failed to create button task");
        return;
    }

    ESP_ERROR_CHECK(gpio_install_isr_service(0));
    ESP_ERROR_CHECK(gpio_isr_handler_add(
        BOOT_BUTTON_GPIO, boot_button_isr, NULL));

    /* 按下 BOOT 时由高变低，触发下降沿中断 */
    ESP_ERROR_CHECK(gpio_set_intr_type(
        BOOT_BUTTON_GPIO, GPIO_INTR_NEGEDGE));
    ESP_ERROR_CHECK(gpio_intr_enable(BOOT_BUTTON_GPIO));

    ESP_LOGI(TAG, "BOOT button ready: GPIO0");
}

/* Private functions */
/*
 *  Stack event callback functions
 *      - on_stack_reset is called when host resets BLE stack due to errors
 *      - on_stack_sync is called when host has synced with controller
 */
static void on_stack_reset(int reason) {
    /* On reset, print reset reason to console */
    ESP_LOGI(TAG, "nimble stack reset, reset reason: %d", reason);
}

static void on_stack_sync(void)
{
    /* 蓝牙同步后，先启动广播 */
    adv_init();

    /* 只初始化一次，避免蓝牙重新同步时重复创建任务 */
    static bool button_initialized = false;

    if (!button_initialized) {
        boot_button_init();
        button_initialized = true;
    }
}

static void nimble_host_config_init(void) {
    /* Set host callbacks */
    ble_hs_cfg.reset_cb = on_stack_reset;
    ble_hs_cfg.sync_cb = on_stack_sync;
    ble_hs_cfg.store_status_cb = ble_store_util_status_rr;

    /* Store host configuration */
    ble_store_config_init();
}

static void nimble_host_task(void *param) {
    /* Task entry log */
    ESP_LOGI(TAG, "nimble host task has been started!");

    /* This function won't return until nimble_port_stop() is executed */
    nimble_port_run();

    /* Clean up at exit */
    vTaskDelete(NULL);
}

void app_main(void) {
    /* Local variables */
    int rc = 0;
    esp_err_t ret = ESP_OK;

    /* NVS flash initialization */
    ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
        ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "failed to initialize nvs flash, error code: %d ", ret);
        return;
    }

    /* NimBLE host stack initialization */
    ret = nimble_port_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "failed to initialize nimble stack, error code: %d ",
                 ret);
        return;
    }

#if CONFIG_BT_NIMBLE_GAP_SERVICE
    /* GAP service initialization */
    rc = gap_init();
    if (rc != 0) {
        ESP_LOGE(TAG, "failed to initialize GAP service, error code: %d", rc);
        return;
    }
#endif

    /* NimBLE host configuration initialization */
    nimble_host_config_init();

    /* Start NimBLE host task thread and return */
    xTaskCreate(nimble_host_task, "NimBLE Host", 4*1024, NULL, 5, NULL);
    return;
}

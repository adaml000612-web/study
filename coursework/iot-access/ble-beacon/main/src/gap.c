/*
 * SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */
/* Includes */
#include "gap.h"
#include "common.h"

/* Private function declarations */
inline static void format_addr(char *addr_str, uint8_t addr[]);
static void start_advertising(void);
static void update_lock_adv(void);

/* Private variables */
static uint8_t own_addr_type;
static uint8_t addr_val[6] = {0};
static uint8_t esp_uri[] = {BLE_GAP_URI_PREFIX_HTTPS, '/', '/', 'e', 's', 'p', 'r', 'e', 's', 's', 'i', 'f', '.', 'c', 'o', 'm'};

/* 门锁初始状态：上锁 */
static uint8_t g_lock_status = LOCK_STATUS_LOCKED;

/* 厂商自定义数据：公司标识低字节、高字节、门锁状态 */
static uint8_t g_mfg_data[3] = {
    MANUFACTURER_ID_LOW,
    MANUFACTURER_ID_HIGH,
    LOCK_STATUS_LOCKED
};

/* Private functions */
inline static void format_addr(char *addr_str, uint8_t addr[]) {
    sprintf(addr_str, "%02X:%02X:%02X:%02X:%02X:%02X", addr[0], addr[1],
            addr[2], addr[3], addr[4], addr[5]);
}

/* 填写广播内容，包括门锁状态 */
static void build_adv_fields(struct ble_hs_adv_fields *fields)
{
    memset(fields, 0, sizeof(*fields));

    const char *name = ble_svc_gap_device_name();

    fields->flags =
        BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;

    fields->name = (uint8_t *)name;
    fields->name_len = strlen(name);
    fields->name_is_complete = 1;

    fields->tx_pwr_lvl = BLE_HS_ADV_TX_PWR_LVL_AUTO;
    fields->tx_pwr_lvl_is_present = 1;

    fields->appearance = BLE_GAP_APPEARANCE_GENERIC_TAG;
    fields->appearance_is_present = 1;

    fields->le_role = BLE_GAP_LE_ROLE_PERIPHERAL;
    fields->le_role_is_present = 1;

    /* FF FF 后面的一个字节表示门锁状态 */
    g_mfg_data[2] = g_lock_status;
    fields->mfg_data = g_mfg_data;
    fields->mfg_data_len = sizeof(g_mfg_data);
       /* 计算全部 AD 字段占用的字节数，包括 Length 和 Type */
    size_t need = 3                         /* Flags */
                + (2 + fields->name_len)    /* Device Name */
                + 3                         /* Tx Power */
                + 4                         /* Appearance */
                + 3                         /* LE Role */
                + (2 + fields->mfg_data_len); /* Manufacturer */

    if (need > ADV_MAX_LEN) {
        ESP_LOGE(TAG, "ADV payload %u > %d bytes, name too long!",
                 (unsigned int)need, ADV_MAX_LEN);
    }
}

static void start_advertising(void) {
    /* Local variables */
    int rc = 0;
    struct ble_hs_adv_fields adv_fields = {0};
    struct ble_hs_adv_fields rsp_fields = {0};
    struct ble_gap_adv_params adv_params = {0};


     /* 填写广播字段，包含当前门锁状态 */
    build_adv_fields(&adv_fields);

    /* Set advertisement fields */
    rc = ble_gap_adv_set_fields(&adv_fields);
    if (rc != 0) {
        ESP_LOGE(TAG, "failed to set advertising data, error code: %d", rc);
        return;
    }

    /* Set device address */
    rsp_fields.device_addr = addr_val;
    rsp_fields.device_addr_type = own_addr_type;
    rsp_fields.device_addr_is_present = 1;

    /* Set URI */
    rsp_fields.uri = esp_uri;
    rsp_fields.uri_len = sizeof(esp_uri);

    /* Set scan response fields */
    rc = ble_gap_adv_rsp_set_fields(&rsp_fields);
    if (rc != 0) {
        ESP_LOGE(TAG, "failed to set scan response data, error code: %d", rc);
        return;
    }

    /* Set non-connectable and general discoverable mode to be a beacon */
    adv_params.conn_mode = BLE_GAP_CONN_MODE_NON;
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;

    /* Start advertising */
    rc = ble_gap_adv_start(own_addr_type, NULL, BLE_HS_FOREVER, &adv_params,
                           NULL, NULL);
    if (rc != 0) {
        ESP_LOGE(TAG, "failed to start advertising, error code: %d", rc);
        return;
    }
    ESP_LOGI(TAG, "advertising started!");
}

/* 停止当前广播，再使用最新门锁状态重新启动 */
static void update_lock_adv(void)
{
    int rc;

    if (ble_gap_adv_active()) {
        rc = ble_gap_adv_stop();
        if (rc != 0) {
            ESP_LOGE(TAG, "failed to stop advertising, rc=%d", rc);
            return;
        }
    }

    /*
     * start_advertising() 会调用 build_adv_fields()，
     * 将最新的 g_lock_status 写入厂商数据，
     * 并检查设置广播数据、扫描响应和启动广播的返回值。
     */
    start_advertising();`
}

/* Public functions */
/* 切换门锁状态，并更新广播 */
/* 设置指定门锁状态，并更新广播 */
void set_lock_status(uint8_t status)
{
    if (status != LOCK_STATUS_LOCKED &&
        status != LOCK_STATUS_UNLOCKED) {
        ESP_LOGE(TAG, "invalid lock status: 0x%02X",
                 (unsigned int)status);
        return;
    }

    g_lock_status = status;
    g_mfg_data[2] = status;

    ESP_LOGI(TAG, "=== Lock Status Changed: 0x%02X (%s) ===",
             (unsigned int)status,
             status == LOCK_STATUS_LOCKED ? "LOCKED" : "UNLOCKED");

    update_lock_adv();
}

/* 在上锁和解锁之间切换 */
void toggle_lock_status(void)
{
    uint8_t next_status =
        (g_lock_status == LOCK_STATUS_LOCKED)
            ? LOCK_STATUS_UNLOCKED
            : LOCK_STATUS_LOCKED;

    set_lock_status(next_status);
}

void adv_init(void) {
    /* Local variables */
    int rc = 0;
    char addr_str[18] = {0};

    /* Make sure we have proper BT identity address set */
    rc = ble_hs_util_ensure_addr(0);
    if (rc != 0) {
        ESP_LOGE(TAG, "device does not have any available bt address!");
        return;
    }

    /* Figure out BT address to use while advertising */
    rc = ble_hs_id_infer_auto(0, &own_addr_type);
    if (rc != 0) {
        ESP_LOGE(TAG, "failed to infer address type, error code: %d", rc);
        return;
    }

    /* Copy device address to addr_val */
    rc = ble_hs_id_copy_addr(own_addr_type, addr_val, NULL);
    if (rc != 0) {
        ESP_LOGE(TAG, "failed to copy device address, error code: %d", rc);
        return;
    }
    format_addr(addr_str, addr_val);
    ESP_LOGI(TAG, "device address: %s", addr_str);

    /* Start advertising. */
    start_advertising();
}

int gap_init(void) {
    /* Local variables */
    int rc = 0;

    /* Initialize GAP service */
    ble_svc_gap_init();

    /* Set GAP device name */
    rc = ble_svc_gap_device_name_set(DEVICE_NAME);
    if (rc != 0) {
        ESP_LOGE(TAG, "failed to set device name to %s, error code: %d",
                 DEVICE_NAME, rc);
        return rc;
    }

    /* Set GAP device appearance */
    rc = ble_svc_gap_device_appearance_set(BLE_GAP_APPEARANCE_GENERIC_TAG);
    if (rc != 0) {
        ESP_LOGE(TAG, "failed to set device appearance, error code: %d", rc);
        return rc;
    }
    return rc;
}

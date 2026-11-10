/*
 * SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */
#ifndef COMMON_H
#define COMMON_H

/* Includes */
/* STD APIs */
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

/* ESP APIs */
#include "esp_log.h"
#include "nvs_flash.h"
#include "sdkconfig.h"
#include "driver/gpio.h"
#include "esp_timer.h"

/* FreeRTOS APIs */
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

/* NimBLE stack APIs */
#include "host/ble_hs.h"
#include "host/ble_uuid.h"
#include "host/util/util.h"
#include "nimble/ble.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"

/* Defines */
#define TAG "NimBLE_Beacon"
#define DEVICE_NAME "ESP32_2108"
/* 门锁状态：0 为上锁，1 为解锁 */
#define LOCK_STATUS_LOCKED   0
#define LOCK_STATUS_UNLOCKED 1

/* 板载 BOOT 按键：GPIO0，按下为低电平 */
#define BOOT_BUTTON_GPIO GPIO_NUM_0

/* 按键消抖时间，单位：微秒 */
#define DEBOUNCE_TIME_US 20000

/* 厂商自定义数据：公司标识 0xFFFF，用于本实验 */
#define MANUFACTURER_ID_LOW  0xFF
#define MANUFACTURER_ID_HIGH 0xFF

/* 传统 BLE 广播数据的最大长度，单位：字节 */
#define ADV_MAX_LEN 31

#endif // COMMON_H

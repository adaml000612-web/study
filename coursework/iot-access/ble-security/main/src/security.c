/* Tasks 2/3: shared security state, debounced BOOT input and LED feedback. */
#include "common.h"
#include "security.h"
#include "led.h"
#include "driver/gpio.h"
#include "freertos/semphr.h"

#define BUTTON_GPIO GPIO_NUM_0
#define DEBOUNCE_MS 200
static portMUX_TYPE state_lock = portMUX_INITIALIZER_UNLOCKED;
static security_snapshot_t state;
static SemaphoreHandle_t button_sem;

security_snapshot_t security_snapshot(void) {
    portENTER_CRITICAL(&state_lock);
    security_snapshot_t result = state;
    portEXIT_CRITICAL(&state_lock);
    return result;
}

void security_command(uint8_t cmd) {
    portENTER_CRITICAL(&state_lock);
    if (cmd == 0) { state.armed = 0; state.alarm = 0; }
    else if (cmd == 1) state.armed = 1;
    else if (cmd == 2) state.alarm = 0;
    portEXIT_CRITICAL(&state_lock);
    /* Door is a physical input; acknowledging does not fake a closed door. */
    ESP_LOGI(TAG, "security command=0x%02x (%s)", cmd,
             cmd == 0 ? "DISARMED" : cmd == 1 ? "ARMED" : "ALARM ACKNOWLEDGED");
}

static void IRAM_ATTR button_isr_handler(void *arg) {
    BaseType_t wake = pdFALSE;
    xSemaphoreGiveFromISR(button_sem, &wake);
    if (wake) portYIELD_FROM_ISR();
}

static void sensor_task(void *param) {
    ESP_LOGI(TAG, "sensor task started: BOOT GPIO0, both edges, debounce 200ms");
    /* Also sample once at startup. */
    xSemaphoreGive(button_sem);
    while (1) {
        xSemaphoreTake(button_sem, portMAX_DELAY);
        int level = gpio_get_level(BUTTON_GPIO);
        /* Require a stable level for the debounce interval. */
        do {
            level = gpio_get_level(BUTTON_GPIO);
        } while (xSemaphoreTake(button_sem, pdMS_TO_TICKS(DEBOUNCE_MS)) == pdTRUE);
        if (gpio_get_level(BUTTON_GPIO) != level) {
            xSemaphoreGive(button_sem);
            continue;
        }
        uint8_t door = level == 0;
        portENTER_CRITICAL(&state_lock);
        bool changed = state.door != door;
        if (changed) {
            state.door = door;
            if (door && state.armed) state.alarm = 1;
        }
        security_snapshot_t current = state;
        portEXIT_CRITICAL(&state_lock);
        if (changed) {
            ESP_LOGI(TAG, "door %s; armed=%u alarm=%u", door ? "OPEN" : "CLOSED",
                     current.armed, current.alarm);
            if (current.alarm && door) ESP_LOGW(TAG, "ALARM! door opened while armed!");
            security_notify();
        }
    }
}

static void security_led_task(void *param) {
    unsigned phase = 0;
    uint8_t previous_mode = 255;
    while (1) {
        security_snapshot_t current = security_snapshot();
        uint8_t mode = !current.armed ? 0 : current.alarm ? 2 : 1;
        if (mode != previous_mode) { phase = 0; previous_mode = mode; }
        unsigned half_period = mode == 2 ? 100 : 500;
        if (mode == 0 || phase >= half_period) led_off();
        else led_on();
        phase = (phase + 20) % (half_period * 2);
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

void security_start(void) {
    button_sem = xSemaphoreCreateBinary();
    assert(button_sem);
    gpio_config_t config = {
        .pin_bit_mask = 1ULL << BUTTON_GPIO,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_ANYEDGE,
    };
    ESP_ERROR_CHECK(gpio_config(&config));
    esp_err_t rc = gpio_install_isr_service(0);
    if (rc != ESP_ERR_INVALID_STATE) ESP_ERROR_CHECK(rc);
    ESP_ERROR_CHECK(gpio_isr_handler_add(BUTTON_GPIO, button_isr_handler, NULL));
    assert(xTaskCreate(sensor_task, "Sensor", 4096, NULL, 5, NULL) == pdPASS);
    assert(xTaskCreate(security_led_task, "Security LED", 2048, NULL, 5, NULL) == pdPASS);
}

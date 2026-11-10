# 物联网接入实验归档

本目录保存本地现有工程快照。

- ble-beacon 为 BLE Beacon/GAP 门锁广播工程。广播状态切换已有历史操作记录，原始 ADV/SCAN_RSP 分析及课程要求的软件定时器消抖仍需核验。
- ble-security 为 BLE 安全配对、加密通信与安防扩展工程。历史构建通过，用户曾确认烧录完成。任务二、三的手机端通知、按键报警和 Bonding 重连仍需补充实测证据。

## 构建

使用 ESP-IDF 6.1 环境，在各工程目录运行 `idf.py build`。Security 工程当前配置目标为 ESP32-S3。引脚和目标以工程配置为准。

本次仅归档现有代码和配置。工程运行所需的 managed_components 由组件管理器恢复。

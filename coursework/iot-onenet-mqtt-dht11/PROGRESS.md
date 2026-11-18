# OneNet MQTT 实验阶段性进度

暂停日期：2026-11-18（北京时间）。

## 当前进度

- 已从官方 MQTT SSL 示例建立工程，目标 ESP32-S3，使用 ESP-IDF 6.1。
- 用户已完成配置页填写 Wi-Fi 及 OneNet 参数。
- 已加入自定义 Wi-Fi 连接、SNTP 校时、设备密钥生成 Token、OneNet MQTT 3.1.1 连接及属性设置 Topic 订阅代码。
- 用户报告已完成烧录；本次未独立验证烧录结果、串口日志或设备在线状态。

## 保存检查发现

- 当前 app_main.c 含两个同名 sync_ntp_time() 函数定义，会导致重新编译时报重复定义；为保存真实现场，本快照原样保留，未擅自修改。
- 当前源码与用户刚烧录的固件是否为同一版本尚未核对。暂停前没有可用串口日志证明 Wi-Fi、NTP 或 MQTT 成功。
- 尚未添加 DHT11 驱动、OneJSON 温湿度封装和周期上报；任务二 LED/间隔控制及应答也未实现。

## 下次继续

1. 确认 VS Code 打开的实际工程及已烧录版本，处理重复函数并重新编译。
2. 核对串口，查看 Wi-Fi connected、NTP time synced、Token generated、MQTT_EVENT_CONNECTED 日志，确认 OneNet 在线，保存实验截图要求2。
3. 按实验步骤4接入 DHT11（DATA GPIO4），添加驱动及定时上报，验证云端温湿度数据。

## 快照范围

只保存源码、工程配置模板和官方公开证书。设备真实配置 sdkconfig/sdkconfig.old、Wi-Fi 名称与密码、设备密钥、Token、构建产物、IDE本机路径及自动下载组件不上传。重新构建需在 menuconfig 私下填写真实参数。

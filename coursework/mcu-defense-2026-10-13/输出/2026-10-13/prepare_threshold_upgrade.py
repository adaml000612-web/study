from pathlib import Path
import shutil

base = Path(r'D:\Desktop\Ultrasonic_LCD1602_2026-10-12')
out = Path(r'D:\Documents\ChatGPT\study\实验4\输出\2026-10-13\Ultrasonic_Threshold')
out.mkdir(parents=True, exist_ok=True)
for folder in ('Objects', 'Listings'):
    (out / folder).mkdir(exist_ok=True)
source = (base / 'main.c').read_text(encoding='utf-8-sig')
source = source.replace('sbit ECHO = P1^1;', '''sbit ECHO = P1^1;
sbit KEY_PLUS = P3^2;  /* Wire JP1 K3 to P3.2; pressed = 0. */
sbit KEY_MINUS = P3^3; /* Wire JP1 K4 to P3.3; pressed = 0. */
unsigned int limit_cm = 30;
unsigned char key_candidate = 0;
unsigned char key_samples = 0;
unsigned char key_stable = 0;
bit key_armed = 1;''', 1)
source = source.replace('lcd_write(0x80,0); lcd_text("Ultrasonic Range");',
                        'lcd_write(0x80,0); lcd_text("Dist: --- cm    ");', 1)
source = source.replace('lcd_write(0xC0,0); lcd_text("Starting...     ");',
                        'lcd_write(0xC0,0); lcd_text("Limit: 030 cm   ");', 1)
source = source.replace('lcd_write(0xC0,0); lcd_text(line);',
                        'lcd_write(0x80,0); lcd_text(line);', 1)
helpers = '''/* Threshold is displayed independently on LCD row 2. */
void lcd_limit(void)
{
    char line[17] = "Limit: 000 cm   ";
    line[7] = limit_cm / 100 + '0';
    line[8] = (limit_cm / 10) % 10 + '0';
    line[9] = limit_cm % 10 + '0';
    lcd_write(0xC0,0);
    lcd_text(line);
}

/* Called during idle only: 3 matching samples, about 20ms or longer.
 * Release must also be debounced before accepting another press.
 * Both keys pressed together consume the press without changing limit.
 * No interrupt is used and no key/LCD operation runs during Echo timing.
 */
void keys_poll(void)
{
    unsigned char raw;
    raw = 0;
    if(KEY_PLUS == 0) raw |= 1;
    if(KEY_MINUS == 0) raw |= 2;
    if(raw != key_candidate) {
        key_candidate = raw;
        key_samples = 1;
    } else if(key_samples < 3) {
        key_samples++;
    }
    if(key_samples < 3 || raw == key_stable) return;
    key_stable = raw;
    if(raw == 0) {
        key_armed = 1;
        return;
    }
    if(!key_armed) return;
    key_armed = 0;
    if(raw == 1 && limit_cm < 200) {
        limit_cm += 5;
        lcd_limit();
    } else if(raw == 2 && limit_cm > 5) {
        limit_cm -= 5;
        lcd_limit();
    }
}

/* Scan keys in 10ms idle slices, instead of blocking for 200ms. */
void idle_with_keys(void)
{
    unsigned char i;
    for(i = 0; i < 20; i++) {
        keys_poll();
        delay_ms(10);
    }
}

'''
assert source.count('void main(void)') == 1
source = source.replace('void main(void)', helpers + 'void main(void)', 1)
source = source.replace('EA=0; TRIG=0; ECHO=1;',
                        'EA=0; TRIG=0; ECHO=1; KEY_PLUS=1; KEY_MINUS=1;', 1)
source = source.replace('uart_init(); delay_ms(200); lcd_init();',
                        'uart_init(); delay_ms(200); lcd_init(); lcd_limit();', 1)
source = source.replace('lcd_write(0xC0,0); lcd_text("NO ECHO         ");',
                        'lcd_write(0x80,0); lcd_text("NO ECHO         ");', 1)
assert source.count('        delay_ms(200);') == 1
source = source.replace('        delay_ms(200);', '        idle_with_keys();', 1)
(out / 'main.c').write_text(source, encoding='utf-8')
project = (base / 'Ultrasonic_LCD1602.uvproj').read_text(encoding='utf-8-sig')
project = project.replace('Ultrasonic_LCD1602', 'Ultrasonic_Threshold')
(out / 'Ultrasonic_Threshold.uvproj').write_text(project, encoding='utf-8')
readme = '''阈值设置升级版（第一阶段，未启用蜂鸣器）

原工程保留：D:/Desktop/Ultrasonic_LCD1602_2026-10-12
打开：Ultrasonic_Threshold.uvproj
烧录文件：Objects/Ultrasonic_Threshold.hex（以build.log成功生成记录为准）
芯片：STC89C516RD+；11.0592MHz；12T，Enable 6T不勾选。

断电后连接两根杜邦线：
独立按键模块JP1的K3 -> 单片机J29/P32（P3.2）
独立按键模块JP1的K4 -> 单片机J29/P33（P3.3）
这是板上独立按键模块，不是矩阵键盘S1～S16，也不是复位RSTK1。
独立按键按下为低电平，依据普中A5(V5.5)教程PDF第225～226页。
K3/K4不要同时连接到其他模块。板载按键已共地，不另接电源。
超声波及LCD接线保持原来的P1.0/P1.1、P0、P2.6/P2.5/P2.7。
P3.0/P3.1用于下载和串口，保留原下载跳线，不用它们接按键。

功能与预期：
第一行：Dist: xx cm；无有效回波时显示NO ECHO。
第二行：Limit: 030 cm；K3加5，K4减5，边界5～200 cm。
按住不连发，松开后再按才再次触发；两键同时稳定按下不改值。
关机/复位恢复30 cm，本版不保存EEPROM，不比较阈值报警。
三次相同扫描消抖；扫描在约10ms空闲片段之间，显示操作会延长间隔。
测量Echo期间不扫描按键、不操作LCD；极短按键有可能漏检，请明确按下约0.15～0.3秒。
200ms改成20段约10ms等待，维持测量间隔并在其间扫描按键。
串口仍9600 8N1；原有串口发送轮询尚未增加超时。

硬件验收（待用户完成，不冒充实测通过）：
1. 上电第二行30 cm，第一行继续随目标距离变化。
2. K3短按一次到35，K4短按一次回30。
3. 按住K3两秒只增加一次，松开后再次按再增加一次。
4. 反复调整，在200/5边界不越界；复位恢复30。
5. 无回波时第二行阈值仍在，按键仍可操作（测量超时期间响应会延后）。
6. 若按键无效，先核对JP1的K3/K4到P32/P33，避免错接矩阵键盘。
'''
(out / '使用说明.txt').write_text(readme, encoding='utf-8-sig')
print(out)

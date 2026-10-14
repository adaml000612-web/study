from pathlib import Path

base = Path(r'D:\Desktop\Ultrasonic_Threshold_2026-10-13')
out = Path(r'D:\Documents\ChatGPT\study\实验4\输出\2026-10-13\Ultrasonic_Alarm')
out.mkdir(parents=True, exist_ok=True)
for name in ('Objects', 'Listings'):
    (out / name).mkdir(exist_ok=True)
s = (base / 'main.c').read_text(encoding='utf-8-sig')
s = s.replace('bit key_armed = 1;', '''bit key_armed = 1;
sbit BEEP = P1^5; /* P1.5 -> J7, PNP driver: high = off. */
bit alarm_on = 0;
bit last_valid = 0;
bit status_dirty = 0;
unsigned int last_cm = 0;

/* T2 auto-reload: 230 ticks per half period, about 2 kHz at 12T.
 * Internal clock, EXEN2=0: P1.0/P1.1 remain ultrasonic GPIOs.
 */
void timer2_isr(void) interrupt 5 using 1
{
    TF2 = 0;
    EXF2 = 0;
    BEEP = !BEEP;
}

void buzzer_init(void)
{
    BEEP = 1;
    T2CON = 0x00;
    RCAP2H = 0xFF;
    RCAP2L = 0x1A;
    TH2 = 0xFF;
    TL2 = 0x1A;
    ET2 = 1;
    EA = 1;
}

void buzzer_pause(void)
{
    TR2 = 0;
    TF2 = 0;
    BEEP = 1;
}

void buzzer_resume(void)
{
    buzzer_pause();
    if(alarm_on) {
        TH2 = 0xFF;
        TL2 = 0x1A;
        TR2 = 1;
    }
}

/* Entry <= limit; exit >= limit+3; invalid data silences alarm.
 * last_cm/last_valid are updated only by completed measurements.
 */
void alarm_evaluate(void)
{
    bit previous;
    previous = alarm_on;
    if(!last_valid) alarm_on = 0;
    else if(!alarm_on && last_cm <= limit_cm) alarm_on = 1;
    else if(alarm_on && last_cm >= limit_cm + 3) alarm_on = 0;
    if(previous != alarm_on) {
        status_dirty = 1;
        buzzer_resume();
    }
}''', 1)
s = s.replace('char line[17] = "Limit: 000 cm   ";',
              'char line[17] = "Limit: 000 cm  -";', 1)
s = s.replace("line[9] = limit_cm % 10 + '0';", "line[9] = limit_cm % 10 + '0';\n    line[15] = alarm_on ? '!' : '-';\n    status_dirty = 0;", 1)
s = s.replace('limit_cm += 5;\n        lcd_limit();',
              'limit_cm += 5;\n        alarm_evaluate();\n        lcd_limit();', 1)
s = s.replace('limit_cm -= 5;\n        lcd_limit();',
              'limit_cm -= 5;\n        alarm_evaluate();\n        lcd_limit();', 1)
s = s.replace('EA=0; TRIG=0; ECHO=1; KEY_PLUS=1; KEY_MINUS=1;',
              'EA=0; BEEP=1; TRIG=0; ECHO=1; KEY_PLUS=1; KEY_MINUS=1;', 1)
s = s.replace('uart_init(); delay_ms(200); lcd_init(); lcd_limit();',
              'uart_init(); delay_ms(200); lcd_init(); buzzer_init(); lcd_limit();', 1)
s = s.replace('        ticks=ultrasonic_read();', '''        /* Keep original Echo timing free from buzzer ISR latency. */
        buzzer_pause();
        EA=0;
        ticks=ultrasonic_read();
        EA=1;
        if(ticks==0) last_valid=0;
        else {
            last_valid=1;
            last_cm=(unsigned int)(((unsigned long)ticks*10000UL+267264UL)/534528UL);
        }
        alarm_evaluate();
        buzzer_resume();
        if(status_dirty) lcd_limit();''', 1)
s = s.replace('            distance_cm=(unsigned int)(((unsigned long)ticks*10000UL+267264UL)/534528UL);',
              '            distance_cm=last_cm;', 1)
(out / 'main.c').write_text(s, encoding='utf-8')
p = (base / 'Ultrasonic_Threshold.uvproj').read_text(encoding='utf-8-sig')
(out / 'Ultrasonic_Alarm.uvproj').write_text(p.replace('Ultrasonic_Threshold', 'Ultrasonic_Alarm'), encoding='utf-8')
notes = '''超声波阈值报警升级版（第二阶段）

打开：Ultrasonic_Alarm.uvproj；烧录Objects/Ultrasonic_Alarm.hex。
芯片STC89C516RD+；11.0592MHz；12T，不启用6T。
上一版阈值工程保留，原测距公式与串口9600 8N1保留。

新增一根线：断电后，单片机P15/P1.5 -> 蜂鸣器模块J7的控制端。
J7通常是蜂鸣器附近的单个黄色控制针；不是蜂鸣器本体焊脚、5V电源或继电器端子。
依据普中A5(V5.5)教程PDF第114~117页：蜂鸣器模块独立，PNP三极管驱动，高电平关，低电平导通，示例P15->J7。
该系列教程说明为无源蜂鸣器，因此采用约2kHz方波，不用恒定低电平维持报警。
板载驱动已接电源和地，只连接控制线；不要让IO直接给蜂鸣器供电。
如果实际板上端子丝印与J7不同，先核对近照，不能猜测电源针。

保留接线：K3->P32，K4->P33；Trig->P1.0，Echo->P1.1；LCD不变。
K3加5，K4减5，范围5~200；按住只触发一次；复位恢复30。
第一行距离，第二行Limit: 030 cm  -，末尾!表示报警状态，-表示未报警。
未报警且距离<=阈值时进入报警；已报警且距离>=阈值+3时解除；中间保持状态。
无有效回波：NO ECHO，关闭距离报警；这不代表前方没有障碍物。
调整阈值时根据最近一次有效距离重新判断；下次测量再更新真实距离。
T2独立自动重装产生音频，中断5，寄存器组1；不修改T0/T1。
T2内部时钟且关闭外部触发，避免占用P1.0/P1.1的外部T2/T2EX功能。
测量Echo期间暂停声音、关闭中断，结束后恢复；每轮测量时有短静音，长等待时可听到断续。
没有长时间蜂鸣器阻塞延时。LCD固定延时仍有开销，串口轮询仍没有超时。
阈值设置、回差和固定音调已实现；随距离加快鸣叫、滤波、EEPROM保存未实现。

实物验收（尚待用户验证）：
1. 默认30，目标40cm：安静，状态-。
2. 靠近到25cm：响，状态!，距离仍刷新。
3. 移到31~32cm：保持响；移到至少33cm：停止。
4. 把阈值调整到目标距离以上/以下，确认进入及解除判断。
5. 按住键不连续改变；测不到回波时NO ECHO且静音。
6. 响时移开目标，确认测距及按键没有卡住。
读数采用整数厘米且未滤波；边界测试以LCD实际读数为准，也要用尺子核对。
如果显示!但没声音，先检查P15->J7及引脚丝印；如果显示-却持续响，核对接线与驱动类型。
'''
(out / '使用说明.txt').write_text(notes, encoding='utf-8-sig')
print(out)

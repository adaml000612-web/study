from pathlib import Path

base = Path(r'D:\Desktop\Ultrasonic_Alarm_2026-10-13')
out = Path(r'D:\Documents\ChatGPT\study\实验4\输出\2026-10-13\Ultrasonic_Proximity')
out.mkdir(parents=True, exist_ok=True)
for name in ('Objects', 'Listings'):
    (out / name).mkdir(exist_ok=True)
s = (base / 'main.c').read_text(encoding='utf-8-sig')
start = s.index('/* T2 auto-reload:')
end = s.index('/* STC89C516RD+', start)
s = s[:start] + '''/* Shared with ISR. All main-side changes are made with EA=0. */
volatile unsigned int quiet_ms = 450;
volatile unsigned int phase_ms = 0;
volatile unsigned char quarter_count = 0;
volatile bit burst_on = 0;

/* T2 half period = 230 ticks (~249.57 us); 4 IRQs ~= 1 ms.
 * The same T2 drives a ~2kHz tone and the nonblocking burst envelope.
 * No T0 access, LCD call or long delay occurs in this ISR.
 */
void timer2_isr(void) interrupt 5 using 1
{
    TF2 = 0;
    EXF2 = 0;
    quarter_count++;
    if(quarter_count >= 4) {
        quarter_count = 0;
        if(alarm_on) {
            if(phase_ms != 0) phase_ms--;
            if(phase_ms == 0) {
                burst_on = !burst_on;
                phase_ms = burst_on ? 50 : quiet_ms;
            }
        }
    }
    if(alarm_on && burst_on) BEEP = !BEEP;
    else BEEP = 1;
}

void buzzer_init(void)
{
    EA = 0;
    BEEP = 1;
    T2CON = 0x00; /* Internal clock; EXEN2=0, no T2/T2EX pin use. */
    RCAP2H = 0xFF;
    RCAP2L = 0x1A;
    TH2 = 0xFF;
    TL2 = 0x1A;
    TF2 = 0;
    EXF2 = 0;
    ET2 = 1;
    TR2 = 1;
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
    /* Preserve phase_ms/burst_on so a measurement does not restart bursts. */
    EA = 0;
    buzzer_pause();
    TH2 = 0xFF;
    TL2 = 0x1A;
    TR2 = 1;
    EA = 1;
}

/* Entry <= limit; exit >= limit+3. Invalid data silences alarm.
 * Near <= limit/3: 50ms on / 70ms off.
 * Middle <= 2*limit/3: 50ms on / 200ms off.
 * Far alarm region: 50ms on / 450ms off.
 * Times are nominal: Echo measurement pauses the envelope clock.
 */
void alarm_evaluate(void)
{
    bit previous;
    unsigned int new_quiet;
    new_quiet = 450;
    if(last_valid) {
        if(last_cm * 3UL <= limit_cm) new_quiet = 70;
        else if(last_cm * 3UL <= (unsigned long)limit_cm * 2UL) new_quiet = 200;
    }
    EA = 0;
    previous = alarm_on;
    if(!last_valid) alarm_on = 0;
    else if(!alarm_on && last_cm <= limit_cm) alarm_on = 1;
    else if(alarm_on && last_cm >= limit_cm + 3) alarm_on = 0;
    quiet_ms = new_quiet;
    if(previous != alarm_on) {
        status_dirty = 1;
        burst_on = alarm_on;
        phase_ms = alarm_on ? 50 : 0;
        quarter_count = 0;
    } else if(alarm_on && !burst_on && phase_ms > quiet_ms) {
        /* Shorten a pending silence when the target becomes nearer. */
        phase_ms = quiet_ms;
    }
    if(!alarm_on) BEEP = 1;
    EA = 1;
}

''' + s[end:]
(out / 'main.c').write_text(s, encoding='utf-8')
p = (base / 'Ultrasonic_Alarm.uvproj').read_text(encoding='utf-8-sig')
(out / 'Ultrasonic_Proximity.uvproj').write_text(p.replace('Ultrasonic_Alarm', 'Ultrasonic_Proximity'), encoding='utf-8')
notes = '''距离分级短鸣版

工程：Ultrasonic_Proximity.uvproj
烧录：Objects/Ultrasonic_Proximity.hex
保留旧按键版与持续报警版；11.0592MHz，12T，不启用6T。
接线不变：K3->P32，K4->P33；P15->蜂鸣器J7；超声波和LCD不变。

报警规则与旧版一致：<=阈值进入，>=阈值+3解除，中间保持；无有效回波静音。
默认阈值30cm，每按K3/K4加减5cm，范围5~200cm，复位恢复30cm。
默认30cm阈值下，三档：
21~30cm（以及回差区中仍保持报警时）：响约50ms，停约450ms。
11~20cm：响约50ms，停约200ms。
0~10cm中的有效测量：响约50ms，停约70ms。
调整阈值后分档同步按阈值的1/3、2/3改变，而非固定10、20。
失败返回0不是0cm，不能进入最近档；无回波会关闭报警。
这是改变鸣叫节奏，短鸣瞬间的音量未降低，也没有改变音调。
LCD末尾!表示处于报警状态，并非每个短鸣此刻是否正在响；-表示未报警。

技术说明：
T2约2kHz音调，每4次中断推进约1ms的响/停状态，不使用长阻塞延时。
两次测量之间按键继续扫描；不重设T0/T1来生成蜂鸣器节奏。
回波测量时暂停T2与声音并关闭中断，测完恢复且不重置短鸣阶段。
因此50/450/200/70ms是名义定时，跨测量窗口的实际间隔可能较长，短鸣也可能分段。
16位共享倒计时由主程序在EA=0时更新，防止ISR读到半更新值。
原始测距公式、整数四舍五入、无滤波和原串口轮询保留。
反复测量时不能在每轮重新开始50ms短鸣，否则会破坏节奏，本版保存阶段。

硬件验收（尚待用户测试）：
1. 默认30cm，目标40cm应安静。
2. 靠近25cm慢速短鸣；15cm中速；5~8cm快速。
3. 从25cm报警退到31~32cm保持，再到>=33cm停止。
4. 按键调整阈值时LCD继续更新，调整后分档随阈值变化。
5. 目标移开/无回波时静音；复位恢复30cm。
6. 观察快速鸣叫时读数和按键仍正常；若短鸣仍太响，下一步再单独验证降低驱动占空比。
'''
(out / '使用说明.txt').write_text(notes, encoding='utf-8-sig')
print(out)

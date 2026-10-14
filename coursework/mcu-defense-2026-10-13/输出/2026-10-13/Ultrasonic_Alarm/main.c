#include <REG52.H>
sbit TRIG = P1^0;
sbit ECHO = P1^1;
sbit KEY_PLUS = P3^2;  /* Wire JP1 K3 to P3.2; pressed = 0. */
sbit KEY_MINUS = P3^3; /* Wire JP1 K4 to P3.3; pressed = 0. */
unsigned int limit_cm = 30;
unsigned char key_candidate = 0;
unsigned char key_samples = 0;
unsigned char key_stable = 0;
bit key_armed = 1;
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
}

/* STC89C516RD+, 11.0592 MHz, 12T, UART 9600 8N1 */
void timer0_start(void)
{
    TR0=0; TH0=0; TL0=0; TF0=0; TR0=1;
}
void wait_ticks(unsigned int ticks)
{
    unsigned int preload;
    TR0=0;
    preload=0-ticks;
    TH0=(unsigned char)(preload>>8);
    TL0=(unsigned char)preload;
    TF0=0; TR0=1;
    while(TF0==0);
    TR0=0; TF0=0;
}
void delay_ms(unsigned int ms)
{
    while(ms!=0) { wait_ticks(922); ms--; }
}
void uart_init(void)
{
    TMOD=0x21;
    PCON &= 0x7F;
    SCON=0x50;
    TH1=0xFD; TL1=0xFD;
    TF1=0; TI=0; TR1=1;
}
void uart_send_char(unsigned char ch)
{
    SBUF=ch;
    while(TI==0);
    TI=0;
}
void uart_send_text(char *text)
{
    while(*text!='\0') { uart_send_char(*text); text++; }
}
void uart_send_number(unsigned int value)
{
    unsigned char digits[5];
    unsigned char index;
    index=0;
    do {
        digits[index]=value%10+'0';
        value=value/10;
        index++;
    } while(value!=0);
    while(index!=0) { index--; uart_send_char(digits[index]); }
}
unsigned int ultrasonic_read(void)
{
    unsigned int ticks;
    ECHO=1; TRIG=0;
    if(ECHO!=0) return 0;
    TRIG=1; wait_ticks(20); TRIG=0;
    timer0_start();
    while(ECHO==0) {
        if(TF0!=0) { TR0=0; return 0; }
    }
    timer0_start();
    while(ECHO!=0) {
        if(TF0!=0) { TR0=0; return 0; }
    }
    TR0=0;
    if(TF0!=0) return 0;
    ticks=((unsigned int)TH0<<8)|TL0;
    return ticks;
}
sbit LCD_RS=P2^6;
sbit LCD_RW=P2^5;
sbit LCD_E=P2^7;
void lcd_write(unsigned char value,unsigned char is_data)
{
    LCD_E=0; LCD_RS=is_data; LCD_RW=0;
    P0=value;
    wait_ticks(20);
    LCD_E=1; wait_ticks(20); LCD_E=0;
    delay_ms(2);
}
void lcd_text(char *text)
{
    while(*text!='\0') { lcd_write(*text,1); text++; }
}
void lcd_init(void)
{
    LCD_E=0; LCD_RS=0; LCD_RW=0;
    delay_ms(40);
    lcd_write(0x30,0); delay_ms(5);
    lcd_write(0x30,0); delay_ms(2);
    lcd_write(0x30,0);
    lcd_write(0x38,0); lcd_write(0x08,0);
    lcd_write(0x01,0); lcd_write(0x06,0); lcd_write(0x0C,0);
    lcd_write(0x80,0); lcd_text("Dist: --- cm    ");
    lcd_write(0xC0,0); lcd_text("Limit: 030 cm   ");
}
void lcd_distance(unsigned int cm)
{
    char line[17];
    char digits[5];
    unsigned char i,index,pos;
    for(i=0;i<16;i++) line[i]=' ';
    line[16]='\0';
    line[0]='D'; line[1]='i'; line[2]='s'; line[3]='t'; line[4]=':';
    index=0;
    do { digits[index]=cm%10+'0'; cm=cm/10; index++; } while(cm!=0);
    pos=6;
    while(index!=0) { index--; line[pos]=digits[index]; pos++; }
    line[pos]=' '; line[pos+1]='c'; line[pos+2]='m';
    lcd_write(0x80,0); lcd_text(line);
}
/* Threshold is displayed independently on LCD row 2. */
void lcd_limit(void)
{
    char line[17] = "Limit: 000 cm  -";
    line[7] = limit_cm / 100 + '0';
    line[8] = (limit_cm / 10) % 10 + '0';
    line[9] = limit_cm % 10 + '0';
    line[15] = alarm_on ? '!' : '-';
    status_dirty = 0;
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
        alarm_evaluate();
        lcd_limit();
    } else if(raw == 2 && limit_cm > 5) {
        limit_cm -= 5;
        alarm_evaluate();
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

void main(void)
{
    unsigned int ticks;
    unsigned int distance_cm;
    EA=0; BEEP=1; TRIG=0; ECHO=1; KEY_PLUS=1; KEY_MINUS=1;
    uart_init(); delay_ms(200); lcd_init(); buzzer_init(); lcd_limit();
    uart_send_text("ULTRASONIC TEST READY\r\n");
    while(1) {
        /* Keep original Echo timing free from buzzer ISR latency. */
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
        if(status_dirty) lcd_limit();
        if(ticks==0) {
            uart_send_text("NO ECHO\r\n"); lcd_write(0x80,0); lcd_text("NO ECHO         ");
        } else {
            distance_cm=last_cm;
            lcd_distance(distance_cm); uart_send_text("DIST=");
            uart_send_number(distance_cm);
            uart_send_text(" cm, TICKS=");
            uart_send_number(ticks);
            uart_send_text("\r\n");
        }
        idle_with_keys();
    }
}
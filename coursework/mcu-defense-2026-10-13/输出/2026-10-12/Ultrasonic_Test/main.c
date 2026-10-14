#include <REG52.H>
sbit TRIG = P1^0;
sbit ECHO = P1^1;

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
void main(void)
{
    unsigned int ticks;
    unsigned int distance_cm;
    EA=0; TRIG=0; ECHO=1;
    uart_init(); delay_ms(200);
    uart_send_text("ULTRASONIC TEST READY\r\n");
    while(1) {
        ticks=ultrasonic_read();
        if(ticks==0) {
            uart_send_text("NO ECHO\r\n");
        } else {
            distance_cm=(unsigned int)(((unsigned long)ticks*10000UL+267264UL)/534528UL);
            uart_send_text("DIST=");
            uart_send_number(distance_cm);
            uart_send_text(" cm, TICKS=");
            uart_send_number(ticks);
            uart_send_text("\r\n");
        }
        delay_ms(200);
    }
}
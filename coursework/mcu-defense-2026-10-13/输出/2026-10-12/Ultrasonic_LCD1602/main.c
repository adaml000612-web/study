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
    lcd_write(0x80,0); lcd_text("Ultrasonic Range");
    lcd_write(0xC0,0); lcd_text("Starting...     ");
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
    lcd_write(0xC0,0); lcd_text(line);
}
void main(void)
{
    unsigned int ticks;
    unsigned int distance_cm;
    EA=0; TRIG=0; ECHO=1;
    uart_init(); delay_ms(200); lcd_init();
    uart_send_text("ULTRASONIC TEST READY\r\n");
    while(1) {
        ticks=ultrasonic_read();
        if(ticks==0) {
            uart_send_text("NO ECHO\r\n"); lcd_write(0xC0,0); lcd_text("NO ECHO         ");
        } else {
            distance_cm=(unsigned int)(((unsigned long)ticks*10000UL+267264UL)/534528UL);
            lcd_distance(distance_cm); uart_send_text("DIST=");
            uart_send_number(distance_cm);
            uart_send_text(" cm, TICKS=");
            uart_send_number(ticks);
            uart_send_text("\r\n");
        }
        delay_ms(200);
    }
}
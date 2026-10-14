#include <REG52.H>
/* Pin mapping from local Prechin A5 tutorial, PDF page 390. */
sbit LCD_RS=P2^6;
sbit LCD_RW=P2^5;
sbit LCD_E=P2^7;
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
void lcd_write(unsigned char value,unsigned char is_data)
{
    LCD_E=0;
    LCD_RS=is_data;
    LCD_RW=0;
    P0=value;
    wait_ticks(20);
    LCD_E=1;
    wait_ticks(20);
    LCD_E=0;
    delay_ms(2);
}
void lcd_init(void)
{
    LCD_E=0; LCD_RS=0; LCD_RW=0;
    delay_ms(40);
    lcd_write(0x30,0); delay_ms(5);
    lcd_write(0x30,0); delay_ms(2);
    lcd_write(0x30,0);
    lcd_write(0x38,0);
    lcd_write(0x08,0);
    lcd_write(0x01,0);
    lcd_write(0x06,0);
    lcd_write(0x0C,0);
}
void lcd_text(char *text)
{
    while(*text!='\0') { lcd_write(*text,1); text++; }
}
void main(void)
{
    EA=0;
    TMOD=0x01;
    lcd_init();
    lcd_write(0x80,0);
    lcd_text("LCD TEST OK");
    lcd_write(0xC0,0);
    lcd_text("0123456789ABCDEF");
    while(1);
}
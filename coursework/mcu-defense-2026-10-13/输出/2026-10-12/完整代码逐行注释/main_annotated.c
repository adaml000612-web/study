/* 完整实验逐行注释版：保留原程序语句和执行顺序，仅增加说明。 */
/* 条件：STC89C516RD+，11.0592 MHz，12T；Keil C51 中 unsigned int 为16位，unsigned long为32位。 */
/* 本程序采用轮询，无中断服务；延时和Echo计时共用T0，串口波特率使用T1。 */
#include <REG52.H> // 引入8052寄存器定义，例如P0、P1、TMOD、TH0、TL0、SCON等。
sbit TRIG = P1^0; // 给P1.0取位变量名TRIG，连接超声波触发输入；这里^是sbit声明中的位选择。
sbit ECHO = P1^1; // 给P1.1取位变量名ECHO，读取超声波模块的回波输出。

/* STC89C516RD+, 11.0592 MHz, 12T, UART 9600 8N1 */
void timer0_start(void) // 定义T0重新从零开始计时的函数，无参数、无返回值。
{ // timer0_start函数体开始。
    TR0=0; TH0=0; TL0=0; TF0=0; TR0=1; // 停止T0；清高/低计数寄存器；清溢出标志；重新启动T0。
} // timer0_start函数结束。
void wait_ticks(unsigned int ticks) // 等待指定次数的T0计数；当前每次计数约1.08507微秒。
{ // wait_ticks函数体开始。
    unsigned int preload; // 16位初值，决定距离下一次溢出还需计数多少次。
    TR0=0; // 先停止T0，避免写入初值期间继续计数。
    preload=0-ticks; // 按16位无符号回绕得到65536-ticks；本程序传入的ticks均大于0。
    TH0=(unsigned char)(preload>>8); // 右移8位取得初值的高8位，再写入TH0。
    TL0=(unsigned char)preload; // 转为8位类型，取初值的低8位并写入TL0。
    TF0=0; TR0=1; // 清除旧溢出标志，然后开始计数。
    while(TF0==0); // 空循环轮询TF0，直到计数溢出；末尾分号表示循环体为空。
    TR0=0; TF0=0; // 延时结束后停止T0，并清除本次溢出标志。
} // wait_ticks函数结束；函数和指令开销使实际等待略长于纯计数时间。
void delay_ms(unsigned int ms) // 提供近似毫秒延时；ms是要等待的毫秒数。
{ // delay_ms函数体开始。
    while(ms!=0) { wait_ticks(922); ms--; } // 每轮等待922次计数（约1000.43微秒）并减1，直到ms为0。
} // delay_ms函数结束；这是近似延时，并非精确到微秒的毫秒计时。
void uart_init(void) // 初始化串口，以及T0/T1的模式；应在使用上述延时之前执行。
{ // uart_init函数体开始。
    TMOD=0x21; // T1模式2（8位自动重装），T0模式1（16位）；两者内部计时且不门控。
    PCON &= 0x7F; // 按位与01111111，清SMOD最高位，关闭串口倍速并保留PCON其他位。
    SCON=0x50; // 串口模式1、允许接收REN=1、TI/RI清零；本程序仅实现发送处理。
    TH1=0xFD; TL1=0xFD; // 重装值和初值均为253，每3次计数溢出一次；配合当前时钟产生9600波特率。
    TF1=0; TI=0; TR1=1; // 清T1溢出标志和发送标志，再启动T1作为串口波特率时钟。
} // uart_init函数结束；串口帧格式对应电脑上的9600、8位数据、无校验、1停止位。
void uart_send_char(unsigned char ch) // 发送一个8位数据字节；参数也可以是一个ASCII字符。
{ // uart_send_char函数体开始。
    SBUF=ch; // 写发送缓冲寄存器，交给串口硬件通过P3.1/TXD发送。
    while(TI==0); // 轮询等待硬件置TI；模式1中在停止位开始时置位；本函数没有软件超时。
    TI=0; // 软件清除发送标志，为下一次调用做准备。
} // uart_send_char函数结束。
void uart_send_text(char *text) // 接收以空字符结尾的字符串起始地址，逐个发送字符。
{ // uart_send_text函数体开始。
    while(*text!='\0') { uart_send_char(*text); text++; } // 未到结束符就发送当前字符，再让指针移动到下一字符。
} // uart_send_text函数结束；不发送末尾的\0。
void uart_send_number(unsigned int value) // 将16位无符号整数转换成十进制数字字符后发送。
{ // uart_send_number函数体开始。
    unsigned char digits[5]; // 暂存最多5位数字（65535）；按长度读取，不需要字符串结束符。
    unsigned char index; // 记录存入的字符数量，也用于反向读取数组。
    index=0; // 从数组下标0开始存储。
    do { // 先执行一次再判断，使输入0也能生成字符'0'。
        digits[index]=value%10+'0'; // 取个位余数0~9，加字符'0'的编码转换为数字字符。
        value=value/10; // 整数除以10，丢掉已取出的个位。
        index++; // 已存字符数量加1，指向下一个待写位置。
    } while(value!=0); // 还有更高位数字就继续拆分；数组内是从个位到高位的逆序。
    while(index!=0) { index--; uart_send_char(digits[index]); } // 先减下标再读取，按高位到低位的顺序发送。
} // uart_send_number函数结束；只修改参数的局部副本，不修改调用者的变量。
unsigned int ultrasonic_read(void) // 返回Echo高电平的计数值；返回0表示本次无有效测量。
{ // ultrasonic_read函数体开始。
    unsigned int ticks; // 保存停止计时后合成的16位计数值。
    ECHO=1; TRIG=0; // 准双向P1.1先写1以读取外部电平，同时使触发线保持低电平。
    if(ECHO!=0) return 0; // 测量前Echo不是低电平则退出，避免从一个已经开始的脉冲中途计时。
    TRIG=1; wait_ticks(20); TRIG=0; // 产生至少约21.7微秒加软件开销的高脉冲，触发超声波模块。
    timer0_start(); // 第一次计时从零开始，仅用于限制等待Echo上升的时间，不用于距离计算。
    while(ECHO==0) { // Echo仍为低就继续等待；轮询发现高电平后退出。
        if(TF0!=0) { TR0=0; return 0; } // 等待约71.1毫秒仍未开始就停止并返回失败，防止无限等待。
    } // 等待回波开始的循环结束。
    timer0_start(); // 检测到Echo高电平后再次清零并启动T0，开始测量高电平脉宽。
    while(ECHO!=0) { // 高电平期间持续计数，检测到Echo变低后退出。
        if(TF0!=0) { TR0=0; return 0; } // 高电平持续到T0溢出则判定失败；不把回绕值当作有效距离。
    } // 高电平等待循环结束；轮询和启停指令会带来软件测时误差。
    TR0=0; // 停止T0，把计数固定下来，再读取高低寄存器。
    if(TF0!=0) return 0; // 补查退出循环到停止计时之间可能发生的溢出。
    ticks=((unsigned int)TH0<<8)|TL0; // TH0先扩为16位再左移8位，与TL0按位或，合成计数值。
    return ticks; // 把计数值交给主程序；它还不是微秒或厘米数。
} // ultrasonic_read函数结束。
sbit LCD_RS=P2^6; // LCD寄存器选择接P2.6：0为命令，1为字符数据。
sbit LCD_RW=P2^5; // LCD读写选择接P2.5：0写、1读；本程序一直采用写操作。
sbit LCD_E=P2^7; // LCD使能接P2.7，写入时用E高到低的转换锁存数据。
void lcd_write(unsigned char value,unsigned char is_data) // 写一个字节；is_data=0发送命令，=1发送字符。
{ // lcd_write函数体开始。
    LCD_E=0; LCD_RS=is_data; LCD_RW=0; // 先拉低E，设置命令/数据选择，并设置写方向。
    P0=value; // 通过P0的8位总线输出字节，对应LCD的D0~D7；P0需外部上拉。
    wait_ticks(20); // 给数据和RS/RW留出稳定时间，约21.7微秒加软件开销。
    LCD_E=1; wait_ticks(20); LCD_E=0; // E拉高并保持，再拉低，完成本次字节写入。
    delay_ms(2); // 等待LCD执行；采用固定延时，没有读取忙标志BF。
} // lcd_write函数结束；它使用T0，应避免在Echo脉宽计时期间调用。
void lcd_text(char *text) // 从当前位置连续显示一个以\0结尾的字符串。
{ // lcd_text函数体开始。
    while(*text!='\0') { lcd_write(*text,1); text++; } // 每个字符按数据写入，然后指针移到下一字符。
} // lcd_text函数结束；显示位置依赖前面发出的地址命令。
void lcd_init(void) // 按上电初始化顺序设置LCD1602的工作模式和初始内容。
{ // lcd_init函数体开始。
    LCD_E=0; LCD_RS=0; LCD_RW=0; // 使能初始为低，选择命令寄存器，选择写操作。
    delay_ms(40); // 上电后等待约40毫秒，让LCD内部电路稳定。
    lcd_write(0x30,0); delay_ms(5); // 第一次8位接口初始化命令，再额外等待约5毫秒。
    lcd_write(0x30,0); delay_ms(2); // 第二次8位接口初始化命令，再额外等待约2毫秒。
    lcd_write(0x30,0); // 第三次8位接口初始化，帮助确保接口处于已知状态。
    lcd_write(0x38,0); lcd_write(0x08,0); // 0x38：8位总线/2行/5x8点阵；0x08：暂时关闭显示。
    lcd_write(0x01,0); lcd_write(0x06,0); lcd_write(0x0C,0); // 清屏；地址写后递增且不移屏；开显示并关闭光标/闪烁。
    lcd_write(0x80,0); lcd_text("Ultrasonic Range"); // 设置DDRAM地址0x00，即第一行开头，然后显示16字符标题。
    lcd_write(0xC0,0); lcd_text("Starting...     "); // 设置DDRAM地址0x40，即第二行开头，显示启动文字并补空格。
} // lcd_init函数结束。
void lcd_distance(unsigned int cm) // 把厘米数格式化成固定16字符的第二行显示内容。
{ // lcd_distance函数体开始。
    char line[17]; // 16个显示字符加1个字符串结束符，防止字符串读取越界。
    char digits[5]; // 暂存厘米数的十进制数字字符，最多5位。
    unsigned char i,index,pos; // i用于填空格，index记录数字数目，pos记录写入line的位置。
    for(i=0;i<16;i++) line[i]=' '; // 先把16个显示位置全部填空格，覆盖上次显示留下的字符。
    line[16]='\0'; // 在数组最后放字符串结束符，供lcd_text判断终点。
    line[0]='D'; line[1]='i'; line[2]='s'; line[3]='t'; line[4]=':'; // 前5个位置填入Dist:；下标5保留空格。
    index=0; // 从digits[0]开始存储数字。
    do { digits[index]=cm%10+'0'; cm=cm/10; index++; } while(cm!=0); // 从个位开始逆序拆数字，输入0也处理一次。
    pos=6; // 从line[6]开始写数字，即屏幕第二行的第7个字符位置。
    while(index!=0) { index--; line[pos]=digits[index]; pos++; } // 反向读取digits，将数字按正常顺序写入line。
    line[pos]=' '; line[pos+1]='c'; line[pos+2]='m'; // 数字后加入空格和单位cm；最大5位数字也在数组范围内。
    lcd_write(0xC0,0); lcd_text(line); // 光标回到第二行开头，写满16字符，更新距离并清除旧尾部。
} // lcd_distance函数结束；cm是局部参数副本，拆分不会修改主程序的distance_cm。
void main(void) // Keil C51单片机主程序入口，初始化后永久循环工作。
{ // main函数体开始。
    unsigned int ticks; // 保存本次Echo高电平的原始计数，范围0~65535。
    unsigned int distance_cm; // 保存最终厘米整数；本版只显示整数厘米。
    EA=0; TRIG=0; ECHO=1; // 关闭总中断；触发线置低；将Echo引脚准备为读取外部电平。
    uart_init(); delay_ms(200); lcd_init(); // 先配置定时器/串口，再上电等待约200毫秒，然后初始化LCD。
    uart_send_text("ULTRASONIC TEST READY\r\n"); // 发送启动提示，\r\n为回车换行；提示本身不证明测距成功。
    while(1) { // 无限循环，持续测量和显示，直到断电或复位。
        ticks=ultrasonic_read(); // 发起一次测量，接收脉宽计数；0表示失败。
        if(ticks==0) { // 根据返回值进入没有有效回波的处理分支。
            uart_send_text("NO ECHO\r\n"); lcd_write(0xC0,0); lcd_text("NO ECHO         "); // 串口报告失败，LCD第二行写16字符覆盖旧距离。
        } else { // 计数非0，进入距离换算和显示分支。
            distance_cm=(unsigned int)(((unsigned long)ticks*10000UL+267264UL)/534528UL); // 乘前扩为32位整数；系数采用340m/s声速，+半除数实现四舍五入；最后转回16位。
            lcd_distance(distance_cm); uart_send_text("DIST="); // 更新LCD第二行，再向串口发送距离字段前缀。
            uart_send_number(distance_cm); // 把厘米整数转换为数字字符发送。
            uart_send_text(" cm, TICKS="); // 输出厘米单位与原始计数字段前缀。
            uart_send_number(ticks); // 输出本次原始计数，便于核对时间与距离换算。
            uart_send_text("\r\n"); // 完成一条记录后回车换行。
        } // 本次成功或失败分支结束。
        delay_ms(200); // 每轮结束后等待约200毫秒；实际更新周期还包括测量、LCD和串口耗时。
    } // 无限循环体结束；正常运行时不会退出该循环。
} // main函数结束。
/* 距离公式：d(cm)=ticks*(12/11059200)*(34000/2)=ticks*10000/534528。除以2因为声波往返。 */
/* 溢出核对：最大中间值65535*10000+267264=655617264，小于32位无符号上限4294967295。 */
/* 保留实现：本版不是浮点算法，仍包含整数厘米四舍五入；注释没有替你修改该行为。 */

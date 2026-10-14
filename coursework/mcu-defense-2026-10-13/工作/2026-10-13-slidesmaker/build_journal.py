import sys,json,math
from pathlib import Path
ROOT=Path(__file__).parent
SKILL=Path(r'D:\Documents\ChatGPT\study\实验4\工具\slides_maker\skills\slide-maker\scripts')
sys.path.insert(0,str(SKILL))
import deckkit as dk,formats,visual_languages as vl,vl_native2 as vn
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
OUT=Path(r'D:\Documents\ChatGPT\study\实验4\输出\2026-10-13\单片机课设_学术完整答辩')
OUT.mkdir(parents=True,exist_ok=True)
prs=formats.blank_deck('wide13');k=vl.use('journal',prs,platform='win',ground='light')
C={a:RGBColor.from_string(b) for a,b in dict(ink='1B1B1B',mute='5A5A55',green='1F5C46',panel='F1EFE7',blue='27516B',rust='91472C',white='FBFAF6').items()}
def txt(s,x,y,w,h,t,size=19,bold=False,color='ink',serif=False):
    return dk.text(s,x,y,w,h,[[(str(t),size,C[color],bold,False,'Georgia' if serif else 'Arial','SimSun' if serif else 'Microsoft YaHei')]],space_after=0)
def line(s,x,y,x2,y2,color='mute',width=1):
    return dk.connector(s,(x,y),(x2,y2),color=C[color],width=width,arrow=False)
def box(s,x,y,w,h,fill='panel',edge=None):
    return dk.box(s,x,y,w,h,fill=C[fill],line=C[edge] if edge else None)
def labelbox(s,x,y,w,h,title,sub='',color='green'):
    box(s,x,y,w,h,'panel');line(s,x,y,x,y+h,color,3)
    txt(s,x+.16,y+.12,w-.3,.5,title,21,True,color)
    if sub:txt(s,x+.16,y+.75,w-.3,h-.78,sub,18)
def flow(s,labels,y=2.5):
    n=len(labels);w=(11.4-(n-1)*.28)/n
    for i,(a,b) in enumerate(labels):
        x=.96+i*(w+.28)
        if i<n-1:dk.connector(s,(x+w,y+.9),(x+w+.26,y+.9),color=C['green'],width=1.5)
        labelbox(s,x,y,w,2.15,a,b)
def screen(s,x,y,w=6.5):
    box(s,x,y,w,1.7,'green')
    txt(s,x+.25,y+.2,w-.5,.6,'LCD TEST OK',25,True,'white')
    txt(s,x+.25,y+.85,w-.5,.6,'0123456789ABCDEF',25,False,'white')
def bullets(s,items,x=.96,y=2.1,w=11.4,h=4.55):
    step=h/len(items)
    for j,(a,b) in enumerate(items):
        txt(s,x,y+j*step,.52,.45,f'{j+1:02}',17,True,'green')
        txt(s,x+.67,y+j*step,w-.67,.43,a,21,True)
        txt(s,x+.67,y+j*step+.5,w-.72,step-.55,b,17 if w<4.5 else 19)
        if j<len(items)-1:line(s,x+.67,y+(j+1)*step-.14,x+w,y+(j+1)*step-.14,'mute',.4)
def waveform(s):
    x=1.1; y=2.65;w=6.9
    txt(s,x,y-.55,w,.4,'Trig / Echo 时序示意（非实测波形）',17,False,'mute')
    for title,yy,points,col in [('Trig',y+.5,[(0,0),(1,0),(1,-.45),(1.35,-.45),(1.35,0),(6.5,0)],'blue'),('Echo',y+1.75,[(0,0),(2,0),(2,-.65),(5,-.65),(5,0),(6.5,0)],'green')]:
        txt(s,x,yy-.65,1.3,.4,title,19,True,col)
        for a,b in zip(points,points[1:]):line(s,x+a[0],yy+a[1],x+b[0],yy+b[1],col,2)
    txt(s,x+2,y+2.1,3.3,.5,'高电平宽度 t → 往返时间',18,True,'green')
    txt(s,x,y+3.05,6.8,.6,'d = v × t / 2',30,True,serif=True)
def footer(s,i,row):
    src=row.get('source','')
    if isinstance(src,(list,dict)):src=json.dumps(src,ensure_ascii=False)
    src=str(src).replace('D:/Documents/ChatGPT/study/实验4/输出/','').replace('D:\\Documents\\ChatGPT\\study\\实验4\\输出\\','')
    if len(src)>110:src=src[:107]+'…'
    txt(s,.96,7.03,11.4,.25,src,9.5,False,'mute')
def render_row(row,i):
    s=k.new_slide();title=row['title'];items=row.get('items',[])
    items=[(v.get('heading',''),v.get('content',v.get('text',''))) if isinstance(v,dict) else tuple(v) for v in items]
    if i==1:
        k.cover(s,title='基于51单片机的\n超声波测距与分级报警',subtitle='从元器件独测到交互报警的完整实验过程',authors='单片机课程实验 · 2026年10月13日',kicker='实验研究报告',abstract='以 STC89C516RD+、SR04 与 LCD1602 建立测距显示链路，逐步加入按键阈值、回差判断与距离分级短鸣。报告沿实验顺序说明基础原理、接口连接、程序实现与已有验证。')
    else:
        vn.jn_running(k,s,{'running':'单片机课程实验  /  '+str(row.get('section','实验原理与实现'))})
        txt(s,.94,.92,11.45,1.0,title,30,True,serif=True)
        code=row.get('code') or row.get('code_snippet')
        if isinstance(code,dict):code=code.get('text',code.get('snippet',''))
        if code:
            if isinstance(code,list):code='\n'.join(code)
            if i==10:code=code.replace('=', '=\n    ',1).replace('+267264UL','\n        +267264UL')
            lines=code.splitlines()
            if len(lines)>14:
                lines=lines[:3]+['/* ... excerpt ... */']+lines[-10:]
            if i==14:lines=[v[8:] if v.startswith('        ') else v for v in lines]
            if i==14:
                lines=['while(1) {','    ticks=ultrasonic_read();','    if(ticks==0) {','        /* NO ECHO output omitted */','    } else {','        /* conversion shown on slide 10 */','        lcd_distance(distance_cm);','        /* UART output omitted */','    }','    delay_ms(200);','}']
            if i==9:
                lines=['timer0_start();','while(ECHO==0) {','    if(TF0!=0) { TR0=0; return 0; }','}','timer0_start();','while(ECHO!=0) {','    if(TF0!=0) { TR0=0; return 0; }','}','TR0=0;','if(TF0!=0) return 0;','ticks=((unsigned int)TH0<<8)|TL0;','return ticks;']
            if i==18:
                lines=['if(raw != key_candidate) {','    key_candidate = raw;','    key_samples = 1;','} else if(key_samples < 3) {','    key_samples++;','}','if(key_samples < 3 || raw == key_stable)','    return;','key_stable = raw;','if(raw == 0) {','    key_armed = 1; return;','}','if(!key_armed) return;','key_armed = 0;']
            if i==25:
                lines=['quarter_count++;','if(quarter_count >= 4) {','    quarter_count = 0;','    if(alarm_on) {','        if(phase_ms != 0) phase_ms--;','        if(phase_ms == 0) {','            burst_on = !burst_on;','            phase_ms = burst_on ?','                50 : quiet_ms;','        }','    }','}','if(alarm_on && burst_on) BEEP = !BEEP;','else BEEP = 1;']
            code='\n'.join(lines)
            dk.code_block(s,.96,2.12,7.05,code,size=16,lang='c',panel=C['panel'],text_c=C['ink'],line_numbers=False,line_h=.285)
            txt(s,1.1,6.5,6.8,.3,'实际源码节选 · 完整函数见原工程与讲者备注',12,False,'mute')
            if i==10:
                txt(s,1.12,3.75,6.5,.6,'N × 1.085 μs  →  t / 58',28,True,'green',True)
                txt(s,1.12,4.65,6.5,1.2,'加上分母的一半再相除\n实现非负整数的四舍五入',23)
            bullets(s,items,x=8.35,y=2.12,w=4.0,h=4.65)
        elif i==6:
            waveform(s);bullets(s,items,x=8.45,y=2.15,w=3.9,h=4.65)
        elif i==11:
            screen(s,1.05,2.45);bullets(s,items,x=8.0,y=2.1,w=4.25,h=4.65)
            txt(s,1.05,4.6,6.4,1.35,'先让两行固定字符完整出现，再接入动态距离。\n图示为预期显示内容，非实物照片。',21)
        elif row.get('type')=='process' and len(items)<=4:
            flow(s,items)
            chains={2:'超声独测 → LCD独测 → 基础整合 → 阈值 → 回差 → 分级短鸣',5:'确认12T → 接好下载跳线 → 下载完成 → 9600串口观察',7:'触发SR04 → 记录TICKS → 换算DIST → 串口观察',19:'扫描按键 → 等待10ms → 重复20段 → 下一次测量',26:'暂停T2并静音 → 轮询Echo计时 → 恢复原节奏状态',28:'暂停声音 → 测距 → 更新报警 → 恢复声音 → 显示 → 扫描按键'}
            txt(s,.98,5.4,11.2,1.0,chains.get(i,title),22,True,'green')
        elif row.get('type')=='compare' and len(items)<=4:
            for j,(a,b) in enumerate(items):
                yy=2.1+j*1.1;txt(s,1.0,yy,3.1,.8,a,22,True,'green');txt(s,4.3,yy,7.9,.97,b,20);line(s,1,yy+1.02,12.25,yy+1.02,'mute',.5)
            if i==23:
                for j,(name,quiet) in enumerate([('近：≤ L/3',70),('中：L/3 < d ≤ 2L/3',200),('远：报警区其余',450)]):
                    yy=4.65+j*.62;txt(s,1,yy,2.9,.4,name,17,True,'green')
                    box(s,4.15,yy,.65,.35,'green');box(s,4.8,yy,quiet/80,.35,'panel')
                    txt(s,4.15,yy+.35,7.6,.25,f'响50ms / 静{quiet}ms（名义值，测量时暂停）',11,False,'mute')
            elif i==22:
                flowlabels=[('T0','Echo计时 / 程序延时'),('T1','串口9600波特率'),('T2','音调 / 响停包络')]
                for j,(a,b) in enumerate(flowlabels):labelbox(s,1+j*3.8,4.7,3.5,1.35,a,b)
        elif row.get('type')=='diagram' and len(items)<=3:
            bullets(s,items,x=5.05,y=2.12,w=7.2,h=4.65)
            diagrams={3:[('SR04 / K3、K4','回波信号 / 阈值输入'),('STC89C516RD+','测距换算 · 状态判断'),('LCD / 蜂鸣模块','数字显示 · 声音提醒')],4:[('P1.0 → Trig','Echo → P1.1'),('P0 → LCD数据','P2.6 / P2.5 / P2.7'),('P3.2 / P3.3 → 按键','P1.5 → J7控制端')],12:[('RS：命令 / 数据','RW=0：写入模式'),('P0：8位数据总线','先放置数据，再产生E脉冲'),('E：使能脉冲','完成一次命令或字符写入')],15:[('T0：Echo计时','测量结束后停止计数'),('T0：LCD延时','顺序复用，同步执行'),('16字符覆盖写入','不足补空格，避免旧字符')],17:[('K3 / K4独立按键','P3.2 / P3.3输入'),('稳定3次 → 单次操作','步进5cm；范围5～200cm'),('默认阈值30cm','松手后才可再次触发')],20:[('距离 ≤ L','进入报警状态'),('L < 距离 < L+3','保持之前的状态'),('距离 ≥ L+3','退出报警；无回波也关闭')],21:[('T2每约250μs中断','翻转一次P1.5电平'),('完整周期约500μs','输出约2kHz方波'),('PNP驱动无源模块','低电平导通；高电平关闭')]}
            labs=diagrams.get(i,[('晶振11.0592MHz','12T工作模式'),('T0频率921600Hz','单次计数约1.085μs'),('16位计数 N','高低字节组合后换算')])
            for j,(lab,sub) in enumerate(labs):
                if j<2:dk.connector(s,(2.62,3.08+j*1.35),(2.62,3.43+j*1.35),color=C['green'],width=2)
                box(s,1.05,2.15+j*1.5,3.5,1.15,'panel')
                txt(s,1.18,2.28+j*1.5,3.25,.4,lab,18,True,'green')
                txt(s,1.18,2.8+j*1.5,3.25,.45,sub,15)
        else:bullets(s,items)
        footer(s,i,row)
    notes=row.get('notes','')
    dk.speaker_notes(s,str(notes)+'\n\n来源：'+str(row.get('source',''))+'\n\n'+str(row.get('code','')))
    if not s.shapes.title:dk.a11y_title(s,title,ea='Microsoft YaHei')
    return s
raw=json.loads((ROOT/'revised_slides.json').read_text(encoding='utf-8-sig'))
rows=raw if isinstance(raw,list) else raw['slides']
for i,row in enumerate(rows,1):render_row(row,i)
dest=OUT/'超声波测距与分级报警_完整学术汇报.pptx'
prs.save(dest)
(OUT/'逐页讲稿.md').write_text('\n\n'.join(f"## {i}. {r['title']}\n\n{r.get('notes','')}\n\n来源：{r.get('source','')}" for i,r in enumerate(rows,1)),encoding='utf-8')
print(json.dumps({'pptx':str(dest),'slides':len(rows),'core':sum(bool(r.get('core')) for r in rows)},ensure_ascii=False))

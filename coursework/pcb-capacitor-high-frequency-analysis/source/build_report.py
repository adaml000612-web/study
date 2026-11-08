from pathlib import Path
import re
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import fitz

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont('Song', 'C:/Windows/Fonts/simsun.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('Hei', 'C:/Windows/Fonts/simhei.ttf'))
pages = [
[
('h','一、背景与概述'),
('p','随着无线通信向高频和高速发展，PCB上的电容除了储能，还常用于电源去耦、信号隔直和阻抗匹配。我们在低频分析中通常把电容看成理想元件，认为频率越高，容抗越小，因此它应该更容易把高频噪声旁路到地。但在实际射频电路中，同一个贴片电容换一个封装或安装位置，滤波效果就可能变化。到了GHz频段，甚至会出现噪声增大、匹配变差等现象。'),
('p','本文主要讨论多层陶瓷贴片电容（MLCC）。这里的高频失效，是指电容在目标频段不能完成预期功能，其中不少器件用电容表测量仍然正常。过压、开裂等造成的实际损坏也需要排查，但不能只凭高频效果不好就判断元件已经烧坏。分析时应同时考虑器件本身、焊盘、走线和接地回路。'),
('h','二、高频失效的主要现象'),
('p','第一种现象是去耦能力下降。例如射频芯片工作时，电源引脚会产生快速变化的电流。若旁路路径在相应频率上阻抗偏高，噪声就不能充分流向地，电源电压会波动，并可能影响接收灵敏度或使输出出现杂散。第二种现象是串联隔直电容影响信号传输，使插入损耗增大、反射增强。用于匹配网络时，寄生参数还可能让最佳匹配频点偏离设计值。'),
('p','这些变化通常与频率有关。电容的阻抗幅值可能先下降，在某一频率附近达到低点，然后又上升。并联多个电容后，也可能在某段频率出现阻抗峰值。可见低频测得的容量只能反映部分特性，不能直接说明它在GHz频段是否合适。'),
('p','排查时还应结合使用位置判断。电源旁路电容关心的是噪声电流经过的整体路径，信号通路中的电容则直接参与传输和匹配。即使都是同一频率，两个位置的设计目标也可能不同。若更换电容后通信质量变化，需要比较相同供电、相同测试条件下的结果，避免把连接松动或测试环境变化误认为电容参数的影响。'),
('h','三、失效机理分析'),
('s','1. 从静电场模型到实际元件'),
('p','在静电近似下，金属导体内部电场为零，表面为等势面，表面外侧电场的切向分量为零。介质界面满足电场切向分量连续，电位移法向分量之差等于自由面电荷密度。结合电极形状和介电常数，可以由电荷与电压的关系得到C＝Q/U。平行板近似C＝εA/d，说明电容与介质、电极面积及间距有关。'),
('p','射频下电荷和电流快速变化，电极与连接路径会产生磁场，导体也存在有限电阻。元件内部尺寸相对波长较小时，可以用集中参数模型近似；若连接路径的电长度已经明显，就还要考虑传播延迟、耦合和分布参数。静电模型能帮助理解电容的形成，但单靠一个容量数值不足以描述高频工作状态。'),
('s','2. ESR与ESL的来源'),
('p','ESR是等效串联电阻，用来表示电极、端头以及介质损耗等带来的能量消耗。高频时趋肤效应和邻近效应会改变电流分布，所以ESR通常随频率变化。通过电容的有效值电流较大时，损耗可近似写成P＝I²ESR，温升过高会影响可靠性。ESL是等效串联电感，主要与内部电极、端头及电流路径的几何结构有关。安装后的焊盘、走线和过孔还会增加回路电感。[1]'),
],
[
('s','3. 自谐振频率与阻抗变化'),
('p','把实际电容近似为C、ESR和ESL串联，忽略对本次讨论影响较小的漏电支路，可得到下面的模型。这个模型适合解释主要趋势，实际设计仍应查看厂商给出的阻抗曲线或高频模型。'),
('fig',''),
('eq','Z＝ESR＋j[2πf·ESL－1/(2πfC)]'),
('eq','fSRF＝1/[2π√(ESL·C)]'),
('p','低于自谐振频率fSRF时，容抗项占优势，元件主要呈容性。两项电抗相等时发生串联自谐振，在参数近似不变的模型中，阻抗幅值降到约ESR。超过这一频率后，感抗项占优势，阻抗逐渐上升，元件主要呈感性。因此，频率升高后容抗虽然继续减小，总阻抗却不一定减小。实际参数随频率变化，最低阻抗点与公式估算值也可能有偏差。[1]'),
('p','例如只作数量级估算，取C＝100 nF、ESL＝0.5 nH，计算得到自谐振频率约22.5 MHz。在1 GHz时，感抗约3.14 Ω，而理想容抗只有约0.0016 Ω，此时寄生电感已明显占主导。这些是假设参数，并非某一型号的实测数据。小容量器件可能有更高的自谐振频率，不能把全部贴片电容都看成到GHz就一定失效。'),
('s','4. PCB安装与反谐振的影响'),
('p','电容离芯片较远时，即使它本身ESL很低，长走线和远处接地过孔也会增加安装电感。电流快速变化会产生u＝L·di/dt的电压，造成电源引脚上的干扰。高频回流倾向沿邻近参考平面、在信号路径下方形成较小回路；地平面开槽或跨分割会迫使回流绕行，增加回路面积和耦合。因此，原理图中同样的接地符号，在实物中可能有不同的高频阻抗。'),
('p','不同容量电容并联时，各支路的自谐振频率不同。在两个谐振点之间，一个支路可能呈感性，另一个仍呈容性，支路电纳相互抵消，形成并联网络的反谐振，使总阻抗出现峰值。峰值大小取决于ESR、安装电感和其他网络参数。若噪声正好落在这个频段，并联后效果可能变差，所以不能把容量相加就认为整个频带的阻抗都会降低。[3]'),
('p','还要注意，较低ESR能够减少损耗和谐振点附近的阻抗，但也会减小网络阻尼，使某些反谐振峰更尖锐。因此低损耗与平坦阻抗需要结合起来考虑。另外，电容与稳压器输出阻抗、电源平面和其他滤波元件也会相互作用。把单颗电容的曲线直接当作整块板的去耦结果，往往会漏掉这些影响。'),
('h','四、通信射频过程中的规避措施'),
('s','1. 根据用途选择电容'),
('p','先区分电源去耦、隔直和匹配三种用途。去耦应关注噪声频谱和允许的电源波动；隔直应检查整个信号频带的传输损耗及反射；匹配电容还应关注精度、品质因数和寄生参数。射频小容量位置可优先考虑容量稳定、损耗较低的C0G/NP0陶瓷电容。较大容量去耦可按需要选择X7R等介质，但要查看直流偏压、温度和老化引起的有效容量变化。'),
],
[
('p','选型时同时检查容量、额定电压、封装、阻抗曲线和自谐振频率。较小封装通常有利于减小连接电感，但也受耐压、容量和装配能力限制。保持明显容性工作时，应留意工作频率与自谐振频率的关系；旁路电容在谐振附近可能阻抗较低，因此最终要看目标频带的实际阻抗。不能仅凭容量大或自谐振频率高就认定某个型号更好。'),
('s','2. 缩短布局与接地路径'),
('p','去耦电容应尽量靠近所服务的电源引脚，并使电源引脚、电容和地之间形成紧凑回路。连接线尽量短，在工艺允许时适当加宽，接地过孔靠近电容地端。必要时采用多个合理布置的过孔，但也要考虑过孔之间的互感。若元件摆得很近却绕长线接地，改善仍可能有限。[2]'),
('p','射频信号线下方应尽量有连续参考地，避免随意跨越地平面分割。换层处需要安排邻近接地过孔，给回流提供连续路径。对射频系统，不能机械套用低频单点接地方法，让所有高频电流经细长地线汇到一点。串联隔直及匹配元件还应沿信号路径紧凑放置，减少多余支线和焊盘造成的不连续。'),
('s','3. 检查并联网络与阻尼'),
('p','多种容量并联可以扩展有效去耦范围，但应把各电容的ESR、ESL和安装寄生一起考虑，检查是否在关注频段出现反谐振峰。可通过调整容量组合、减少不必要的支路、优化安装位置或引入适当阻尼降低峰值。有时利用具有一定ESR的支路就能增加阻尼，是否另加电阻应按电路需求计算，不能为压低峰值而使整个电源阻抗过高。'),
('s','4. 用仿真和测试确认'),
('p','设计初期可利用厂商模型计算阻抗随频率的变化，条件允许时再考虑焊盘、过孔和走线的电磁影响。制作样板后，可用阻抗分析仪或矢量网络分析仪检查相关频段，注意校准和夹具去嵌，避免把测试线的寄生误认为元件特性。电源纹波测试应采用短接地弹簧等低电感连接。最后还要检查整机的灵敏度、输出频谱或误码表现，确认修改确实改善了目标问题。'),
('p','若发现阻抗峰与干扰频率接近，可以先改变一个因素再复测，例如缩短接地路径或调整其中一颗电容。记录修改前后的频点和幅度，比同时更换多种器件更容易判断原因。对于供电去耦，也可用允许电压波动除以相应电流变化，估算目标阻抗，再检查关注频段内是否满足要求。'),
('h','五、结论'),
('p','贴片电容在高频下出现功能失效，主要原因是实际元件包含ESR和ESL，安装结构又增加了寄生参数。自谐振前后，电容的阻抗和相位会明显变化，多电容并联还可能形成反谐振。对通信射频电路，合理做法是从用途和频带出发选型，缩短电源与接地回路，并结合模型和实测检查效果。通过这次分析，我认识到电容容量相同并不代表高频性能相同，原理图正确也需要合适的PCB布局才能发挥作用。'),
('h','参考资料'),
('ref','[1] Murata. What are impedance/ ESR frequency characteristics in capacitors? 2013.\nhttps://article.murata.com/en-eu/article/impedance-esr-frequency-characteristics-in-capacitors'),
('ref','[2] Analog Devices. MT-101: Decoupling Techniques. 2009.\nhttps://www.analog.com/MT-101'),
('ref','[3] ROHM. FAQ 2637，多频率去耦及并联电容的反谐振问题.\nhttps://www.rohm.com/products/faq-search/faqId/2637'),
]
]

styles = {
 'p': ParagraphStyle('body',fontName='Song',fontSize=10.7,leading=16.7,firstLineIndent=21.4,spaceAfter=5,wordWrap='CJK'),
 'h': ParagraphStyle('head',fontName='Hei',fontSize=12,leading=19,spaceBefore=5,spaceAfter=5),
 's': ParagraphStyle('sub',fontName='Hei',fontSize=10.7,leading=17,spaceBefore=3,spaceAfter=3),
 'eq': ParagraphStyle('equation',fontName='Song',fontSize=11,leading=19,alignment=1,spaceAfter=4),
 'ref': ParagraphStyle('reference',fontName='Song',fontSize=8,leading=11,spaceAfter=3,wordWrap='CJK'),
}
pdf = OUT/'PCB贴片电容高频失效分析.pdf'
c=canvas.Canvas(str(pdf),pagesize=A4)
c.setTitle('PCB贴片电容高频失效分析')
c.setAuthor('')
W,H=A4
alltext=[]
for n, blocks in enumerate(pages,1):
 y=H-43
 if n==1:
  c.setFont('Hei',18); c.drawCentredString(W/2,y-14,'PCB贴片电容高频失效分析'); y-=43
 for kind,t in blocks:
  if kind=='fig':
   c.setStrokeColorRGB(0.15,0.15,0.15)
   c.line(110,y-20,145,y-20); c.rect(145,y-26,56,12)
   c.line(201,y-20,235,y-20)
   path=c.beginPath(); path.moveTo(235,y-20)
   for k in range(4): path.curveTo(235+k*14,y,249+k*14,y,249+k*14,y-20)
   c.drawPath(path); c.line(291,y-20,335,y-20)
   c.line(335,y-31,335,y-9); c.line(343,y-31,343,y-9); c.line(343,y-20,480,y-20)
   c.setFont('Song',10); c.drawCentredString(173,y-42,'ESR'); c.drawCentredString(264,y-42,'ESL'); c.drawCentredString(339,y-42,'C')
   c.setFont('Song',9); c.drawCentredString(W/2,y-59,'图1  实际电容的简化串联等效模型（示意）')
   y-=71; continue
  alltext.append(t)
  p=Paragraph(t.replace('&','&amp;').replace('\n','<br/>'),styles[kind])
  _,h=p.wrap(W-92,H)
  y-=styles[kind].spaceBefore
  if y-h<39: raise ValueError(f'Page {n} overflow: {y-h}')
  p.drawOn(c,46,y-h); y-=h+styles[kind].spaceAfter
 c.setFont('Song',9); c.drawCentredString(W/2,23,f'{n} / 3')
 c.showPage()
c.save()
(OUT/'报告正文.txt').write_text('PCB贴片电容高频失效分析\n\n'+'\n\n'.join(alltext),encoding='utf-8')
doc=fitz.open(pdf)
for i,p in enumerate(doc): p.get_pixmap(matrix=fitz.Matrix(1.8,1.8)).save(str(OUT/f'报告第{i+1}页.png'))
body=''.join(t for blocks in pages for k,t in blocks if k in ('p','h','s','eq'))
print('Chinese characters:',len(re.findall(r'[\u4e00-\u9fff]',body)))
print('Pages:',len(doc))
for i,p in enumerate(doc): print(i+1,len(p.get_text()))

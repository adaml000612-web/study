from pathlib import Path
from copy import deepcopy
import json,re,hashlib,zipfile
from PIL import Image
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH

B=Path(__file__).resolve().parent.parent
OUT=B/'deliverables';OUT.mkdir(exist_ok=True)
E=B/'evidence'; C=B/'generated-crops';C.mkdir(exist_ok=True)
jobs=json.loads((B/'verification/jobs.json').read_text(encoding='utf8'))
ras=json.loads((B/'verification/ra_jobs.json').read_text(encoding='utf8'))
results=json.loads((B/'verification/mysql_results.json').read_text(encoding='utf8'))
reference=B/'inputs/report-template.docx'
d=Document(reference)
source_p=list(d.paragraphs)
for p in source_p[19:]:p._element.getparent().remove(p._element)

def replace(p,text):
    fmt=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
    for child in list(p._p):
        if child.tag!=qn('w:pPr'):p._p.remove(child)
    r=p.add_run(text)
    if fmt is not None:r._r.insert(0,fmt)
replace(source_p[3],'班级：物联241       姓名：霍仁博       学号：202412902108')
replace(source_p[13],'Windows 电脑，MySQL 8.4.11，Navicat Premium Lite 18，relaX 关系代数计算器。')

def font(r,name='宋体',size=11,bold=False):
    r.font.name=name;r.font.size=Pt(size);r.bold=bold;r.font.color.rgb=RGBColor(0,0,0)
    r._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),name)

def para(text='',bold=False,size=11,keep=False):
    p=d.add_paragraph();p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(5)
    p.paragraph_format.line_spacing=1.15;p.paragraph_format.keep_with_next=keep
    p.paragraph_format.widow_control=True
    font(p.add_run(text),size=size,bold=bold)
    return p

def heading(text,level=1):
    p=para(text,True,12 if level==1 else 11,True)
    p.paragraph_format.space_before=Pt(9)
    return p

def code(text):
    p=para(size=9.5)
    p.paragraph_format.keep_together=True;p.paragraph_format.keep_with_next=True;p.paragraph_format.space_after=Pt(5)
    for i,line in enumerate(text.splitlines()):
        r=p.add_run(('\n' if i else '')+line);font(r,'Consolas',9)
    return p

def table(headers,rows):
    t=d.add_table(rows=1,cols=len(headers));t.style='Table Grid'
    for cell,value in zip(t.rows[0].cells,headers):
        cell.text=str(value)
        for r in cell.paragraphs[0].runs:font(r,size=10,bold=True)
    for row in rows:
        cells=t.add_row().cells
        for cell,value in zip(cells,row):
            cell.text=str(value)
            for p in cell.paragraphs:
                p.paragraph_format.space_after=Pt(2);p.paragraph_format.space_before=Pt(2)
                for r in p.runs:font(r,size=10)
    for row in t.rows[:-1]:
        for cell in row.cells:
            for p in cell.paragraphs:p.paragraph_format.keep_with_next=True
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    return t

fig=0
def image(path,caption,width=6.4):
    global fig
    p=d.add_paragraph();p.paragraph_format.space_after=Pt(1);p.paragraph_format.keep_with_next=True
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run().add_picture(str(path),width=Inches(width))
    fig+=1
    p=para(f'图 {fig}  {caption}',size=9);p.alignment=WD_ALIGN_PARAGRAPH.CENTER

def native(job):
    queries=[q.strip()+';' for q in job['sql'].split(';') if q.strip()]
    for i,q in enumerate(queries):
        raw=E/f"{job['id']}_{i}.png"
        if not raw.exists():raise FileNotFoundError(raw)
        im=Image.open(raw)
        # Two explicitly identified crops of the same captured window preserve
        # the code and result while excluding the empty editor space.
        lines=sum(max(1,(len(line)+65)//66) for line in q.splitlines())
        code_end=min(420,215+lines*18)
        a=C/f"{job['id']}_{i}_code.png";im.crop((303,185,865,code_end)).save(a)
        rows=results.get(job['id'],[])
        count=len(rows[i]) if i<len(rows) else {('m01',1):4,('v01',1):3}.get((job['id'],i),1)
        bottom=min(838,510+max(1,min(14,count))*24)
        if job['error']:bottom=655 if job['id']!='g09' else 595
        b=C/f"{job['id']}_{i}_result.png";im.crop((303,428,865,bottom)).save(b)
        p=d.add_paragraph();p.paragraph_format.keep_with_next=True;p.paragraph_format.space_after=Pt(1)
        p.add_run().add_picture(str(a),width=Inches(6.4))
        image(b,job['title']+(f' 第{i+1}条语句' if len(queries)>1 else '')+'  同次运行代码区与结果区分别裁剪')
        if i<len(rows):para(f'实际结果为 {count} 行，{len(rows[i][0]) if rows[i] else len(job["reference"][i]["columns"])} 列。',size=10)

def ra(ids):
    for id in ids:
        job=next(j for j in ras if j['id']==id)
        heading(job['title'],2);code(job['query'])
        im=Image.open(E/f'{id}.png').convert('RGB')
        # Locate the real gray node rectangles to include every label and avoid
        # carrying a partially visible result table into the tree screenshot.
        active=[]
        for y in range(560,min(im.height,1020)):
            if sum(65<=im.getpixel((x,y))[0]<=140 and max(im.getpixel((x,y)))-min(im.getpixel((x,y)))<3 for x in range(700,1690))>50:active.append(y)
        groups=[]
        for y in active:
            if not groups or y-groups[-1][-1]>45:groups.append([])
            groups[-1].append(y)
        selected=next(g for g in groups if len(g)>12)
        top,bottom=selected[0],selected[-1]
        xs=[x for y in selected for x in range(700,1690) if 65<=im.getpixel((x,y))[0]<=140 and max(im.getpixel((x,y)))-min(im.getpixel((x,y)))<3]
        box=(max(700,min(xs)-18),max(560,top-18),min(1690,max(xs)+19),min(im.height,bottom+19))
        if id=='ra08':box=(box[0],box[1],box[2],970)
        path=C/f'{id}_tree.png';im.crop(box).save(path)
        width=min(6.4,max(1.2,(box[2]-box[0])/125))
        image(path,job['title']+('  运算树上部' if id=='ra08' else '  运算树区域'),width)
        if id=='ra08':
            lower=C/'ra08_tree_lower.png'
            Image.open(E/'ra08_table.png').crop((1085,90,1280,270)).save(lower)
            image(lower,'分组步骤5 排序  同一运算树下部',1.6)

heading('第一部分  实验须知和参数计算')
para('学号为202412902108，末两位为08，按十进制取 NN=8。')
table(['参数','代入过程','计算值'],[
['T1','5000 + 8 × 50','5400'],['T2','4000 + 8 × 100','4800'],['D','(8 mod 27 + 1) × 10','90']])
para('本次排序分步任务使用 T1=5400，分组分步任务使用 T2=4800。D=90用于最终个性化部门补充校验。指导书的基础题与判断题保留原有固定条件，部门60的比较也保持原题条件。')
para('逻辑执行顺序为 FROM / JOIN / ON → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY。分组聚合在HAVING之前形成，最后再生成需要的输出列。')
para('MySQL先完成词法和语法分析，生成解析结构。预处理阶段核对表名、列名、别名及分组合法性，优化器选择访问路径和连接顺序，执行器按所选算子完成扫描、过滤、连接、聚合和排序，再返回结果。逻辑顺序用于理解语义，实际执行计划不要求逐阶段物化临时表。')
heading('数据核对与材料差异',2)
para('现有myemployees数据与本次SQL附件逐行核对一致，四张表记录数分别为107、27、19、23。relaX使用教师另附的hr_dataset文本。部分hiredate日期存在差异，例如100号员工在SQL数据中为1992-04-03，在relaX文本中为1992-03-04。排序、分组和连接的分步校验字段一致，入职时间基础题以MySQL实际数据为准。')
native(jobs[0])

heading('第二部分  排序查询')
heading('1  分步骤校验')
table(['步骤','操作','行数','列数'],[['1','employees','107','11'],['2','salary > 5400','58','11'],['3','投影四个指定字段','58','4'],['4','部门升序 工资降序','58','4']])
ra(['ra01','ra02','ra03','ra04'])
para('步骤3确定保留哪些列，步骤4确定显示顺序。employee_id仍在投影中，记录保持唯一，因此本题投影不会因关系代数去重而减少行数。MySQL逻辑阶段为 FROM employees 取107行 → WHERE筛选至58行，与relaX一致 → SELECT投影4列 → ORDER BY先按department_id升序，同部门内再按salary降序 → 返回58行。')
para('第二排序键只比较第一排序键相同的记录。第一键已经区分的两行，不会因为第二键较大或较小而跨越第一键形成的组。所有排序键均相同时，相对顺序未被指定。')
for job in jobs[1:9]:
    heading(job['title'],2)
    if job['prediction']:para('运行前预测为'+job['prediction'],keep=True)
    para(job['note'],keep=True);native(job)
    if job['id']=='s02':
        im=Image.open(E/'s02_dates.png');path=C/'s02_dates.png';im.crop((303,185,865,838)).save(path)
        image(path,'补充显示入职日期列  入职时间降序验证',5.9)
heading('排序结果核对',2)
table(['候选','第一排序键','第二排序键','判断'],[['A','department_id ASC','salary DESC','符合题意'],['B','salary DESC','department_id ASC','主次颠倒'],['C','department_id ASC','salary ASC','部门内方向错误']])
para('A前三行为178、200、201，B前三行为100、101、102。B中101与102两人同部门且工资相同，截图中出现的相对位置不构成稳定顺序保证。')

heading('第三部分  分组查询')
heading('1  分步骤校验')
table(['步骤','操作','行数','列数'],[['1','employees 见排序步骤1','107','11'],['2','部门编号非空','106','11'],['3','按部门聚合 人数与平均工资','11','3'],['4','平均工资 > 4800','8','3'],['5','平均工资降序','8','3']])
ra(['ra05','ra06','ra07','ra08'])
para('relaX使用 department_id != null 表达该工具支持的非空筛选。MySQL必须写 department_id IS NOT NULL。MySQL中使用 department_id <> NULL 不会得到相同结果，因为与NULL的普通比较产生UNKNOWN。')
para('MySQL逻辑阶段为 FROM取107行 → WHERE排除部门为空记录，保留106行 → GROUP BY形成11组并计算人数和平均工资 → HAVING保留8组 → SELECT输出部门编号、人数、平均工资3列 → ORDER BY按平均工资降序 → 返回8行。指导书填空段将SELECT写在HAVING之前，本文按前面的标准逻辑顺序解释。')
table(['部门编号','人数','平均工资'],[[x['department_id'],x['employee_count'],f"{x['avg_salary']:.6f}"] for x in sorted(results['g01'][0],key=lambda r:-r['avg_salary'])])
for job in jobs[9:19]:
    heading(job['title'],2)
    if job['prediction']:para('运行前预测为'+job['prediction'],keep=True)
    para(job['note'],keep=True);native(job)
heading('分组判断与计数结论',2)
para('判断题只有B能表达正确的聚合筛选。A的WHERE需要逐行判断，而AVG需要一组记录才能计算。C要求一组输出一个last_name，但同一部门存在多个姓，分组键不能唯一确定这个值。严格分组检查可以在执行前暴露这种歧义。')
para('三个COUNT填空依次为107、35、11。COUNT(*)统计记录数，COUNT(列名)只统计该列非NULL的行，COUNT(DISTINCT 列名)进一步对非NULL值去重。分组基础题②中的NULL部门组有1人，因此总计12组，而有效部门不同编号数为11。')

heading('第四部分  连接查询')
heading('1  分步骤校验')
table(['步骤','操作','行数','列数'],[['1a','employees 见排序步骤1','107','11'],['1b','departments','27','4'],['2','部门编号相等的θ连接','106','15'],['3','投影四个指定字段','106','4'],['4','按部门 工资排序后投影','106','4']])
ra(['ra09','ra10','ra11','ra12'])
para('本次使用显式等值θ连接，因此中间表保留两张表的所有字段，列数为11+4=15，重复的department_id、manager_id由表名前缀区分。自然连接会额外比较所有同名列，不能用于替代这里指定的单一连接条件。')
para('题目要求按工资排序，而步骤3投影后已没有salary。relaX中先在15列连接结果上按departments.department_id和salary排序，再投影4列。若在4列投影之后再按salary排序，会因该属性已被移除而报错。该改写保留题目需要的四列和工资排序语义。')
para('MySQL逻辑阶段为 FROM取departments和employees → ON逐行判断部门编号相等 → 保留106行 → SELECT投影4列 → ORDER BY按部门升序、员工工资升序 → 返回。对等值内连接交换左右表，在保持相同输出列和ORDER BY条件时不改变结果集合。排序键相同的行仍可呈现不同相对次序。外连接交换左右表则需要相应调整LEFT和RIGHT语义。')
for job in jobs[19:35]:
    heading(job['title'],2)
    if job['prediction']:para('运行前预测为'+job['prediction'],keep=True)
    para(job['note'],keep=True);native(job)
    if job['id']=='j11':
        para('根据实际数据，各经理下属人数的平方和为 14² + 5² + 1² + 4² + 5² + 5² + 8² + 8² + 8² + 8² + 8² + 6² + 6² + 6² + 6² + 6² + 1² + 1² = 790。每组n名员工可与同组n名员工配对，NULL经理组不参与等值匹配。')
    if job['id']=='j14':
        im=Image.open(E/'j14_names.png');path=C/'j14_names.png';im.crop((303,185,865,560)).save(path)
        image(path,'员工125的错误部门名称Tre与实际名称Shi对照')
heading('连接正确性的检查方法',2)
para('先确认每个字段代表的实体及外键指向，再预测一对多关系下的行数范围。通过主键抽查员工、部门和经理的对应关系，分别检查丢行、重复配对与错配。遇到0行时，应分别核对基础数据、连接键值域和WHERE条件。需要保留无匹配记录时用外连接，并结合COUNT(DISTINCT ...)核对实体数量。')

heading('第五部分  最终验证')
para(jobs[-1]['note']);native(jobs[-1])
para('最终主要结果为工资阈值筛选58人、分组筛选8个部门、员工部门内连接106行、SQL92与SQL99结果一致、Seattle员工18人、笛卡尔积2889行、错误同经理连接790行、错误部门连接22行、错误地点连接0行。')
heading('五  实验总结')
para('本次实验中，我重点区分了排序主次、分组前后筛选和连接条件的实际含义。多字段排序需要逐个指定方向，工资相同的记录如果还要求稳定顺序，应增加员工编号作为后续排序键。通过部门60的对照，我能直接看到把DESC省略后部门内部顺序发生变化。')
para('分组查询中，WHERE负责筛选参与统计的员工，HAVING负责筛选统计形成的部门组。错误1111和1055分别帮助我定位聚合使用阶段和非分组列歧义。三个COUNT的结果也说明，统计前必须先确定是否保留NULL，以及是否需要对编号去重。')
para('连接查询中，错误条件可以正常执行并返回看似合理的行数。抽查103和125后，我发现错误连接同时造成丢行和部门错配。今后检查连接时，我会先明确编号的含义和关联路径，再核对记录数与代表性样本。员工查地点需要通过部门表，自连接需要用别名区分员工与经理两个角色。')
para('relaX运算树让我能观察筛选、投影、聚合和连接每一步的行数变化。遇到排序列在投影后消失的问题时，应先分析属性是否仍然可用，再调整运算顺序。建议实验材料统一两个附件的日期数据，并统一连接题的排序描述，便于对照验证。')

for p in d.paragraphs:
    for run in p.runs:
        if run.font.color.type is not None:run.font.color.rgb=RGBColor(0,0,0)

final=OUT/'2026-11-08-物联241-霍仁博-实验四排序分组连接查询.docx'
d.save(final)
sql='-- 实验四 排序查询 分组查询 连接查询\n-- 物联241 霍仁博 202412902108\n-- NN=8 T1=5400 T2=4800 D=90\n-- 使用现有myemployees；仅执行查询。错误1111、1055、1066为预期验证，请逐项运行。\nUSE myemployees;\n\n'
sql+='\n\n'.join('-- '+j['title']+('\n-- 预期错误 '+str(j['error']) if j['error'] else '')+'\n'+j['sql'] for j in jobs)
(OUT/'实验四实际执行SQL.sql').write_text(sql,encoding='utf8')
(OUT/'实验四relaX分步表达式.txt').write_text('\n\n'.join(j['title']+'\n'+j['query'] for j in ras),encoding='utf8')
sections=[(s.page_width,s.page_height,s.top_margin,s.bottom_margin,s.left_margin,s.right_margin) for s in d.sections]
(B/'artifact.md').write_text(f'''# 学院报告模板使用记录
参考文件 {reference}
SHA256 {hashlib.sha256(reference.read_bytes()).hexdigest()}
原始页数 6 单一A4纵向节
页面几何 {sections}
保留源文件前19段的学院标识 标题 评分签名表 目的 环境 内容与步骤标题
身份栏填入用户确认信息 环境栏填入实际版本 其余题目槽替换为逐项实验正文
页脚沿用原模板PAGE和NUMPAGES字段 使用Word刷新
原有样式 编号 图像 页眉页脚与不透明部件为保留项
新增内容使用宋体11磅 正文1.15倍行距 黑色标题 截图分别裁剪代码和结果并明示裁剪方式
由于运行包没有LibreOffice，调用标准渲染器后记录失败，再以Word导出PDF并逐页生成PNG复核
''',encoding='utf8')
print('report',final,'figures',fig)

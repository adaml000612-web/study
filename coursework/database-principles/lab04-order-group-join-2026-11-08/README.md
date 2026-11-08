# 实验四 排序查询 分组查询 连接查询

数据库原理及应用课程实验，物联241，霍仁博，学号202412902108。

## 交付内容

- `deliverables/` 包含学院格式Word报告、实际执行SQL及relaX分步表达式。
- `evidence/` 保存本次真实Navicat与relaX截图，报告中的代码区和结果区分别裁剪并在图注明示。
- `verification/` 保存本机MySQL查询结果、relaX结果树记录、运行环境和文件校验值。
- `inputs/` 保存本次使用的教师数据和报告模板。
- `source/` 保存报告生成与PDF逐页检查工具。

## 参数与结果

NN=8，T1=5400，T2=4800，D=90。

工资筛选58行，聚合筛选8个部门，员工部门内连接106行。COUNT结果为107、35、11。Seattle员工18行，笛卡尔积2889行，错误同经理自连接790行，错误部门连接22行，错误地点连接0行。

本机MySQL版本8.4.11，启用ONLY_FULL_GROUP_BY。1111、1055、1066属于题目要求验证的预期错误，SQL应逐项执行。查询在已有myemployees库进行，教师SQL包含DROP TABLE，仅作为导入源保留，重现时应使用独立实验环境。

## 材料差异与处理

两个教师数据附件中部分入职日期不同，MySQL结果以SQL附件为准，relaX按其专用文本运行。连接题主要求使用工资排序，后文的员工编号排序描述与主要求不一致。relaX先按工资排序再投影，解决投影后salary不再可用的问题。员工103在错误D中丢失，员工125被误配到Tre，实际部门为Shi。

## 生成报告

安装Python依赖 `python-docx` 和 `Pillow` 后，在本目录运行 `python source/build_report.py`。生成的Word文档可用Word更新页码字段。渲染检查使用Word导出PDF，再运行 `python source/render_pdf.py report.pdf qa`，该脚本需要PyMuPDF和Pillow。

## 验证记录

MySQL导出的40组成功查询结果与教师SQL数据的独立计算逐行比对一致。relaX12个分步表达式均实际运行，记录行列数。报告已导出并逐页检查，评分和教师签名栏交由教师填写。课程平台提交由学生完成。

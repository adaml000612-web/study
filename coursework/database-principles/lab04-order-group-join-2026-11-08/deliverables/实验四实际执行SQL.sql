-- 实验四 排序查询 分组查询 连接查询
-- 物联241 霍仁博 202412902108
-- NN=8 T1=5400 T2=4800 D=90
-- 使用现有myemployees；仅执行查询。错误1111、1055、1066为预期验证，请逐项运行。
USE myemployees;

-- 数据与运行环境核对
SELECT VERSION() AS mysql_version, @@SESSION.sql_mode AS sql_mode;
SELECT 'employees' AS table_name, COUNT(*) AS row_count FROM employees
UNION ALL SELECT 'departments',COUNT(*) FROM departments
UNION ALL SELECT 'jobs',COUNT(*) FROM jobs
UNION ALL SELECT 'locations',COUNT(*) FROM locations;

-- 排序分步骤校验
SELECT employee_id,last_name,department_id,salary
FROM employees WHERE salary>5400
ORDER BY department_id ASC,salary DESC;

-- 基础任务① 按入职时间降序
SELECT * FROM employees ORDER BY hiredate DESC;

-- 基础任务② 有奖金员工按奖金率升序
SELECT employee_id,first_name,last_name,commission_pct
FROM employees WHERE commission_pct IS NOT NULL
ORDER BY commission_pct ASC;

-- 基础任务③ 姓名长度降序
SELECT last_name,CHAR_LENGTH(last_name) AS name_length
FROM employees ORDER BY CHAR_LENGTH(last_name) DESC;

-- 程序判断 A 与 B 前三行
SELECT 'A' AS candidate,employee_id,department_id,salary
FROM employees ORDER BY department_id,salary DESC LIMIT 3;
SELECT 'B' AS candidate,employee_id,department_id,salary
FROM employees ORDER BY salary DESC,department_id LIMIT 3;

-- 程序判断 A 与 C 部门60比较
SELECT 'A' AS candidate,employee_id,department_id,salary
FROM employees WHERE department_id=60
ORDER BY department_id,salary DESC;
SELECT 'C' AS candidate,employee_id,department_id,salary
FROM employees WHERE department_id=60
ORDER BY department_id,salary;

-- 自主探索 列序号排序
SELECT employee_id,salary,last_name FROM employees
ORDER BY 2 DESC LIMIT 8;

-- 自主探索 NULL升序与降序
SELECT employee_id,commission_pct FROM employees
ORDER BY commission_pct ASC LIMIT 8;
SELECT employee_id,commission_pct FROM employees
ORDER BY commission_pct DESC LIMIT 8;

-- 分组分步骤校验
SELECT department_id,COUNT(*) AS employee_count,AVG(salary) AS avg_salary
FROM employees WHERE department_id IS NOT NULL
GROUP BY department_id HAVING AVG(salary)>4800
ORDER BY avg_salary DESC;

-- 基础任务① 每位领导下属平均工资
SELECT manager_id,AVG(salary) AS avg_salary FROM employees
WHERE manager_id IS NOT NULL GROUP BY manager_id
ORDER BY manager_id;

-- 基础任务② 各部门人数降序
SELECT department_id,COUNT(*) AS employee_count FROM employees
GROUP BY department_id ORDER BY employee_count DESC;

-- 基础任务③ 邮箱含a员工的部门最高工资
SELECT department_id,MAX(salary) AS max_salary FROM employees
WHERE LOWER(email) LIKE '%a%' GROUP BY department_id
ORDER BY department_id;

-- 基础任务④ 平均工资大于3000的部门
SELECT department_id,AVG(salary) AS avg_salary FROM employees
WHERE department_id IS NOT NULL GROUP BY department_id
HAVING AVG(salary)>3000 ORDER BY department_id;

-- 基础任务⑤ 有奖金员工最高工资大于12000
SELECT department_id,MAX(salary) AS max_salary FROM employees
WHERE commission_pct IS NOT NULL AND department_id IS NOT NULL
GROUP BY department_id HAVING MAX(salary)>12000;

-- 程序判断 A 聚合误放WHERE
-- 预期错误 1111
SELECT department_id FROM employees
WHERE AVG(salary)>8000 GROUP BY department_id;

-- 程序判断 B HAVING筛选
SELECT department_id FROM employees GROUP BY department_id
HAVING AVG(salary)>8000 ORDER BY department_id;

-- 程序判断 C 非分组列
-- 预期错误 1055
SELECT department_id,last_name,COUNT(*) FROM employees
GROUP BY department_id;

-- 自主探索 三种COUNT
SELECT COUNT(*) AS all_rows,COUNT(commission_pct) AS bonus_rows,
COUNT(DISTINCT department_id) AS distinct_departments
FROM employees;

-- 连接分步骤校验
SELECT d.department_id,d.department_name,e.employee_id,e.last_name
FROM departments d JOIN employees e
ON d.department_id=e.department_id
ORDER BY d.department_id ASC,e.salary ASC;

-- 基础任务① SQL92等值连接
SELECT e.employee_id,e.last_name,d.department_name
FROM employees e,departments d
WHERE e.department_id=d.department_id ORDER BY e.employee_id;

-- 基础任务① SQL99等值连接
SELECT e.employee_id,e.last_name,d.department_name
FROM employees e JOIN departments d
ON e.department_id=d.department_id ORDER BY e.employee_id;

-- 补充验证 外连接保留全部员工与部门
SELECT e.employee_id,e.last_name,d.department_name
FROM employees e LEFT JOIN departments d
ON e.department_id=d.department_id WHERE e.department_id IS NULL;
SELECT COUNT(*) AS all_employees FROM employees e
LEFT JOIN departments d ON e.department_id=d.department_id;
SELECT COUNT(*) AS all_departments,
SUM(e.employee_id IS NULL) AS empty_departments
FROM departments d LEFT JOIN employees e
ON d.department_id=e.department_id;

-- 基础任务② Seattle部门
SELECT d.department_id,d.department_name FROM departments d
JOIN locations l ON d.location_id=l.location_id
WHERE l.city='Seattle' ORDER BY d.department_id;

-- 基础任务③ Seattle员工及错误E修正
SELECT e.employee_id,e.last_name FROM employees e
JOIN departments d ON e.department_id=d.department_id
JOIN locations l ON d.location_id=l.location_id
WHERE l.city='Seattle' ORDER BY e.employee_id;

-- 基础任务④ 员工及对应经理
SELECT e.employee_id,e.last_name,m.last_name AS manager_name
FROM employees e LEFT JOIN employees m
ON e.manager_id=m.employee_id ORDER BY e.employee_id;

-- 程序判断 A 省略连接条件
SELECT employee_id,department_name FROM employees,departments;

-- 程序判断 B CROSS JOIN
SELECT employee_id,department_name FROM employees CROSS JOIN departments;

-- 程序判断 C 正确经理自连接
SELECT e.employee_id,e.last_name,m.last_name AS manager_name
FROM employees e JOIN employees m
ON e.manager_id=m.employee_id ORDER BY e.employee_id;

-- 程序判断 错误自连接
SELECT COUNT(*) AS wrong_join_rows FROM employees e
JOIN employees m ON e.manager_id=m.manager_id;
SELECT e.employee_id,e.manager_id,m.employee_id AS matched_employee
FROM employees e JOIN employees m ON e.manager_id=m.manager_id
WHERE e.employee_id=103 ORDER BY m.employee_id;

-- 程序判断 自连接未起别名
-- 预期错误 1066
SELECT employees.employee_id FROM employees
JOIN employees ON employees.manager_id=employees.employee_id;

-- 程序判断 D 错误部门连接
SELECT e.employee_id,e.last_name,d.department_name
FROM employees e JOIN departments d ON e.manager_id=d.department_id
ORDER BY e.employee_id;

-- 程序判断 D 抽查员工103和125
SELECT e.employee_id,e.manager_id,e.department_id,
bad.department_id AS wrong_department,bad.department_name AS wrong_name,
good.department_name AS correct_name
FROM employees e JOIN departments bad ON e.manager_id=bad.department_id
JOIN departments good ON e.department_id=good.department_id
WHERE e.employee_id IN (103,125);
SELECT employee_id,manager_id,department_id FROM employees
WHERE employee_id IN (103,125);

-- 程序判断 E 错误地点连接
SELECT e.employee_id,e.last_name FROM employees e
JOIN locations l ON e.department_id=l.location_id
WHERE l.city='Seattle';

-- 自主探索 连接前后部门去重计数
SELECT COUNT(DISTINCT department_id) AS all_departments FROM departments;
SELECT COUNT(DISTINCT d.department_id) AS joined_departments
FROM departments d JOIN employees e ON d.department_id=e.department_id;
SELECT d.department_id,d.department_name FROM departments d
LEFT JOIN employees e ON d.department_id=e.department_id
WHERE e.employee_id IS NULL ORDER BY d.department_id;

-- 最终验证 个性化部门及执行计划
SELECT 8 AS NN,5000+8*50 AS T1,4000+8*100 AS T2,
(MOD(8,27)+1)*10 AS D;
SELECT employee_id,last_name,department_id,salary
FROM employees WHERE department_id=90 ORDER BY salary DESC;
EXPLAIN SELECT employee_id,last_name,department_id,salary
FROM employees WHERE salary>5400 ORDER BY department_id,salary DESC;
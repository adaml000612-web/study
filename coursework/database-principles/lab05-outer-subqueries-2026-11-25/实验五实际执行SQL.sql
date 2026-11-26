-- 实验五 外连接与嵌套 NN=8 T3=6400 D1=90 K=5
USE myemployees;

-- v00 运行环境与个性化参数
SELECT VERSION() AS mysql_version,@@SESSION.sql_mode AS sql_mode,@@secure_file_priv AS export_path;
SELECT 8 AS NN,6000+8*50 AS T3,(MOD(8,27)+1)*10 AS D1,MOD(8,5)+2 AS K;

-- o01 分步核对 两表行列数
SELECT 'departments' AS table_name,COUNT(*) AS rows_count,4 AS columns_count FROM departments UNION ALL SELECT 'employees',COUNT(*),11 FROM employees;

-- o02 没有员工的部门 左外连接
SELECT d.department_id,d.department_name,e.last_name
FROM departments d LEFT JOIN employees e ON e.department_id=d.department_id
WHERE e.employee_id IS NULL ORDER BY d.department_id;

-- o03 交换表位置 右外连接验证
SELECT d.department_id,d.department_name,e.last_name
FROM employees e RIGHT JOIN departments d ON e.department_id=d.department_id
WHERE e.employee_id IS NULL ORDER BY d.department_id;

-- o04 连接中间结果及人数分解
SELECT COUNT(*) AS left_rows,COUNT(e.employee_id) AS matched_rows,
SUM(e.employee_id IS NULL) AS unmatched_departments
FROM departments d LEFT JOIN employees e ON e.department_id=d.department_id;

-- o05 基础① 左外连接统计空部门
SELECT COUNT(*) AS empty_departments FROM departments d LEFT JOIN employees e ON e.department_id=d.department_id WHERE e.employee_id IS NULL;

-- o06 基础① 右外连接统计空部门
SELECT COUNT(*) AS empty_departments FROM employees e RIGHT JOIN departments d ON e.department_id=d.department_id WHERE e.employee_id IS NULL;

-- o07 基础② 保留所有员工
SELECT e.employee_id,e.last_name,d.department_name FROM employees e LEFT JOIN departments d ON e.department_id=d.department_id ORDER BY e.employee_id;

-- o08 基础③ 每部门人数含零人部门
SELECT d.department_id,COUNT(e.employee_id) AS employee_count
FROM departments d LEFT JOIN employees e ON e.department_id=d.department_id
GROUP BY d.department_id ORDER BY employee_count DESC,d.department_id;

-- o09 基础④ 员工经理外自连接
SELECT e.employee_id,e.last_name AS employee_name,m.last_name AS manager_name
FROM employees e LEFT JOIN employees m ON e.manager_id=m.employee_id ORDER BY e.employee_id;

-- o10 判断① A 部门作主表
SELECT d.department_id,d.department_name,e.employee_id FROM departments d LEFT JOIN employees e ON d.department_id=e.department_id;

-- o11 判断① B 员工作主表
SELECT d.department_id,d.department_name,e.employee_id FROM employees e LEFT JOIN departments d ON d.department_id=e.department_id;

-- o12 判断② COUNT陷阱对照
SELECT d.department_id,COUNT(*) AS count_star,COUNT(e.employee_id) AS count_employee
FROM departments d LEFT JOIN employees e ON d.department_id=e.department_id
GROUP BY d.department_id ORDER BY d.department_id;

-- o13 判断③ A 高工资条件放ON
SELECT * FROM departments d LEFT JOIN employees e
ON d.department_id=e.department_id AND e.salary>6400;

-- o14 判断③ B 高工资条件放WHERE
SELECT * FROM departments d LEFT JOIN employees e
ON d.department_id=e.department_id WHERE e.salary>6400;

-- o15 探索 FULL OUTER JOIN语法错误
SELECT d.department_id,e.employee_id FROM departments d
FULL OUTER JOIN employees e ON d.department_id=e.department_id;

-- o16 探索 模拟全外连接
SELECT d.department_id,d.department_name,e.employee_id,e.last_name
FROM departments d LEFT JOIN employees e ON d.department_id=e.department_id
UNION ALL
SELECT d.department_id,d.department_name,e.employee_id,e.last_name
FROM employees e LEFT JOIN departments d ON d.department_id=e.department_id
WHERE d.department_id IS NULL;

-- n01 分步① Abel的工资
SELECT salary FROM employees WHERE last_name='Abel';

-- n02 分步③ 比Abel工资高的员工
SELECT employee_id,last_name,salary FROM employees
WHERE salary>(SELECT salary FROM employees WHERE last_name='Abel') ORDER BY employee_id;

-- n03 基础① 工资比Sciarra高
SELECT employee_id,last_name,salary FROM employees WHERE salary>(SELECT salary FROM employees WHERE last_name='Sciarra') ORDER BY employee_id;

-- n04 基础② 工种名称以p开头
SELECT employee_id,salary FROM employees WHERE job_id IN
(SELECT job_id FROM jobs WHERE LOWER(job_title) LIKE 'p%') ORDER BY employee_id;

-- n05 基础③ ANY 部门50任一工资
SELECT employee_id,salary,department_id FROM employees
WHERE department_id<>50 AND salary>ANY(SELECT salary FROM employees WHERE department_id=50) ORDER BY employee_id;

-- n06 基础④ ALL 部门50全部工资
SELECT employee_id,salary,department_id FROM employees
WHERE department_id<>50 AND salary>ALL(SELECT salary FROM employees WHERE department_id=50) ORDER BY employee_id;

-- n07 基础⑤ MIN改写ANY
SELECT employee_id,salary,department_id FROM employees WHERE department_id<>50 AND salary>(SELECT MIN(salary) FROM employees WHERE department_id=50) ORDER BY employee_id;

-- n08 基础⑤ MAX改写ALL
SELECT employee_id,salary,department_id FROM employees WHERE department_id<>50 AND salary>(SELECT MAX(salary) FROM employees WHERE department_id=50) ORDER BY employee_id;

-- n09 判断① A NOT IN含NULL
SELECT department_id,department_name FROM departments WHERE department_id NOT IN(SELECT department_id FROM employees);

-- n10 判断① B 过滤NULL后NOT IN
SELECT department_id,department_name FROM departments WHERE department_id NOT IN(SELECT department_id FROM employees WHERE department_id IS NOT NULL) ORDER BY department_id;

-- n11 判断① 单独检查子查询NULL
SELECT DISTINCT department_id FROM employees ORDER BY department_id;

-- n12 判断② 多行结果给单值比较
SELECT employee_id,salary FROM employees WHERE salary=(SELECT salary FROM employees WHERE department_id=50);

-- n13 判断② 改为IN
SELECT employee_id,salary FROM employees WHERE salary IN(SELECT salary FROM employees WHERE department_id=50) ORDER BY employee_id;

-- n14 判断② 改为等于ANY
SELECT employee_id,salary FROM employees WHERE salary=ANY(SELECT salary FROM employees WHERE department_id=50) ORDER BY employee_id;

-- n15 判断③ ORDER BY加LIMIT
SELECT last_name FROM employees WHERE salary=(SELECT salary FROM employees ORDER BY salary DESC LIMIT 1);

-- n16 判断③ 去掉LIMIT
SELECT last_name FROM employees WHERE salary=(SELECT salary FROM employees ORDER BY salary DESC);

-- n17 探索① IN查地点1700的员工
SELECT * FROM employees WHERE department_id IN(SELECT department_id FROM departments WHERE location_id=1700) ORDER BY employee_id;

-- n18 探索② JOIN等价写法
SELECT e.* FROM employees e JOIN departments d ON e.department_id=d.department_id WHERE d.location_id=1700 ORDER BY e.employee_id;

-- c01 分步① 部门90手工模拟
SELECT employee_id,last_name,salary,(SELECT AVG(salary) FROM employees WHERE department_id=90) AS dept_avg FROM employees WHERE department_id=90 ORDER BY employee_id;

-- c02 分步② 高于本部门平均工资
SELECT e.employee_id,e.last_name,e.department_id,e.salary FROM employees e
WHERE e.salary>(SELECT AVG(salary) FROM employees WHERE department_id=e.department_id) ORDER BY e.employee_id;

-- c03 基础① EXISTS查有员工部门
SELECT department_id,department_name FROM departments d WHERE EXISTS(SELECT 1 FROM employees e WHERE e.department_id=d.department_id) ORDER BY department_id;

-- c04 基础① IN等价验证
SELECT department_id,department_name FROM departments WHERE department_id IN(SELECT department_id FROM employees) ORDER BY department_id;

-- c05 基础② NOT EXISTS查无员工部门
SELECT department_id,department_name FROM departments d WHERE NOT EXISTS(SELECT 1 FROM employees e WHERE e.department_id=d.department_id) ORDER BY department_id;

-- c06 基础③ 各部门最高工资员工
SELECT e.employee_id,e.last_name,e.department_id,e.salary FROM employees e WHERE e.salary=(SELECT MAX(salary) FROM employees WHERE department_id=e.department_id) ORDER BY e.department_id,e.employee_id;

-- c07 判断① NOT EXISTS与NOT IN
SELECT 'NOT EXISTS' AS method,COUNT(*) AS result_rows FROM departments d WHERE NOT EXISTS(SELECT 1 FROM employees e WHERE e.department_id=d.department_id)
UNION ALL SELECT 'NOT IN',COUNT(*) FROM departments WHERE department_id NOT IN(SELECT department_id FROM employees);

-- c08 判断② A 正确引用部门号
SELECT e.employee_id FROM employees e WHERE e.salary>(SELECT AVG(salary) FROM employees WHERE department_id=e.department_id) ORDER BY e.employee_id;

-- c09 判断② B 错把经理号当部门号
SELECT e.employee_id FROM employees e WHERE e.salary>(SELECT AVG(salary) FROM employees WHERE manager_id=e.department_id) ORDER BY e.employee_id;

-- c10 判断③ A 全公司平均工资
SELECT * FROM employees WHERE salary>(SELECT AVG(salary) FROM employees);

-- c11 判断④ EXISTS中的SELECT星号
SELECT department_id,department_name FROM departments d WHERE EXISTS(SELECT * FROM employees e WHERE e.department_id=d.department_id) ORDER BY department_id;

-- c12 探索 同工种均值相关子查询
SELECT e.employee_id,e.last_name,e.job_id,e.salary FROM employees e WHERE e.salary>(SELECT AVG(salary) FROM employees WHERE job_id=e.job_id) ORDER BY e.employee_id;

-- c13 探索 分组连接等价改写
SELECT e.employee_id,e.last_name,e.job_id,e.salary FROM employees e JOIN
(SELECT job_id,AVG(salary) AS avg_salary FROM employees GROUP BY job_id) j
ON e.job_id=j.job_id WHERE e.salary>j.avg_salary ORDER BY e.employee_id;

-- z01 综合一 高于公司均值的部门
SELECT d.department_id,d.department_name,l.city,COUNT(e.employee_id) AS employee_count,ROUND(AVG(e.salary),2) AS avg_salary
FROM departments d JOIN employees e ON d.department_id=e.department_id JOIN locations l ON d.location_id=l.location_id
GROUP BY d.department_id,d.department_name,l.city
HAVING AVG(e.salary)>(SELECT AVG(salary) FROM employees)
ORDER BY avg_salary DESC,d.department_id;

-- z02 综合二 每个地点的部门数和员工数
SELECT l.location_id,l.city,COUNT(DISTINCT d.department_id) AS department_count,COUNT(e.employee_id) AS employee_count
FROM locations l LEFT JOIN departments d ON l.location_id=d.location_id
LEFT JOIN employees e ON d.department_id=e.department_id
GROUP BY l.location_id,l.city ORDER BY employee_count DESC,l.city,l.location_id;

-- z03 综合三 各部门工资前K名
SELECT e.department_id,e.employee_id,e.last_name,e.salary FROM employees e
WHERE e.department_id IS NOT NULL AND
(SELECT COUNT(*) FROM employees x WHERE x.department_id=e.department_id AND x.salary>e.salary)<5
ORDER BY e.department_id,e.salary DESC,e.employee_id;

-- z04 综合四 原错误语句
SELECT d.department_name,l.city FROM departments d JOIN locations l ON d.location_id=l.location_id
WHERE d.department_id NOT IN(SELECT department_id FROM employees);

-- z05 综合四 LEFT JOIN修正版
SELECT d.department_id,d.department_name,l.city FROM departments d
LEFT JOIN employees e ON d.department_id=e.department_id
LEFT JOIN locations l ON d.location_id=l.location_id
WHERE e.employee_id IS NULL ORDER BY d.department_id;

-- z06 综合四 NOT EXISTS修正版
SELECT d.department_id,d.department_name,l.city FROM departments d
LEFT JOIN locations l ON d.location_id=l.location_id
WHERE NOT EXISTS(SELECT 1 FROM employees e WHERE e.department_id=d.department_id) ORDER BY d.department_id;

-- v01 最终核验 参数与边界数据
SELECT 8 AS NN,6400 AS T3,90 AS D1,5 AS K,
(SELECT AVG(salary) FROM employees) AS company_avg,
(SELECT MIN(salary) FROM employees WHERE department_id=50) AS dept50_min,
(SELECT MAX(salary) FROM employees WHERE department_id=50) AS dept50_max,
(SELECT COUNT(*) FROM employees WHERE department_id=50) AS dept50_rows;
SELECT employee_id,last_name,department_id,manager_id FROM employees WHERE department_id IS NULL OR manager_id IS NULL;
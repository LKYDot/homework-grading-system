-- 标准答案初始化 SQL — 在 MySQL 中直接执行即可导入
-- mysql -u root -p homework_db < init_answers.sql

INSERT IGNORE INTO standard_answer (subject, grade, question_key, question_text, standard_answer, question_type, max_score) VALUES
-- 初中数学 二次根式 测试卷 (grade8)
('math', 'grade8', 'math_grade8_01', '下列二次根式中，是最简二次根式的有', 'A', '选择题', 5),
('math', 'grade8', 'math_grade8_02', '成立，则的取值范 围是', 'D', '选择题', 5),
('math', 'grade8', 'math_grade8_03', '若一个长方形的面积为', '6', '计算题', 5),
('math', 'grade8', 'math_grade8_04', '计算：', '6', '计算题', 5),
('math', 'grade8', 'math_grade8_05', '是最简二次根式，则 x可取的最小整数是', '-2', '填空题', 5),
('math', 'grade8', 'math_grade8_06', '计算或化简：', '见解析', '计算题', 20),
('math', 'grade8', 'math_grade8_07', '阅读理解题', '见解析', '解答题', 15),

-- 小学数学 (grade3)
('math', 'grade3', 'math_grade3_001', '计算：23 + 45 = ?', '68', '口算题', 5),
('math', 'grade3', 'math_grade3_002', '计算：3 + 5 = ?', '8', '口算题', 5),
('math', 'grade3', 'math_grade3_003', '一个长方形的长是8厘米，宽是5厘米，周长是多少厘米？', '26', '计算题', 10),
('math', 'grade3', 'math_grade3_004', '判断：1/2 大于 1/3', '正确', '判断题', 3),

-- 小学数学 (grade1)
('math', 'grade1', 'math_grade1_001', '计算：2 + 3 = ?', '5', '口算题', 5),
('math', 'grade1', 'math_grade1_002', '比较大小：5 __ 3（填 > < 或 =）', '>', '填空题', 3),

-- 初中数学 (grade7)
('math', 'grade7', 'math_grade7_001', '解方程：3x + 5 = 20', 'x = 5', '计算题', 10),
('math', 'grade7', 'math_grade7_002', '化简：2(x + 3) - x', 'x + 6', '计算题', 8),

-- 小学语文 (grade3)
('chinese', 'grade3', 'chinese_grade3_001', '请写出一句描写春天的诗句', '春眠不觉晓，处处闻啼鸟', '填空题', 10);


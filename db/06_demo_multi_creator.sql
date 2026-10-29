-- 多创作者演示数据（2026-10-29）
-- 目的：让管理员/不同创作者登录后，看板能看到不同的发布趋势；
-- 可重复执行：先清理 creator3/4/5 的演示账号、角色关系和稿件，再重建。
-- 密码均为 123456（与 creator 相同的 BCrypt 哈希）。

SET NAMES utf8mb4;

DELETE ur FROM sys_user_role ur
JOIN sys_user u ON u.id = ur.user_id
WHERE u.username IN ('creator3', 'creator4', 'creator5');
DELETE FROM biz_article WHERE author_id IN (
  SELECT id FROM (SELECT id FROM sys_user WHERE username IN ('creator3', 'creator4', 'creator5')) t
);
DELETE FROM sys_user WHERE username IN ('creator3', 'creator4', 'creator5');

INSERT INTO sys_user (id, username, password, nickname, status, remark, create_time, update_time, deleted) VALUES
(13, 'creator3', '$2a$10$O9ZF.iT0wujrMuREYXY/deve0kqa72cjCxuwM76eGPGquSAWikA2q', '陈创作', 1, '多账号演示数据', NOW(), NOW(), 0),
(14, 'creator4', '$2a$10$O9ZF.iT0wujrMuREYXY/deve0kqa72cjCxuwM76eGPGquSAWikA2q', '刘创作', 1, '多账号演示数据', NOW(), NOW(), 0),
(15, 'creator5', '$2a$10$O9ZF.iT0wujrMuREYXY/deve0kqa72cjCxuwM76eGPGquSAWikA2q', '周创作', 1, '多账号演示数据', NOW(), NOW(), 0);

INSERT INTO sys_user_role (user_id, role_id) VALUES (13, 3), (14, 3), (15, 3);

-- creator3：持续更新型，14 天内 8 篇
INSERT INTO biz_article (title, content, summary, category_id, author_id, status, risk_level, view_count, publish_time, create_time, update_time, deleted) VALUES
('小户型玄关的 3 个收纳细节', '玄关是家里最容易乱的地方。用顶天立地鞋柜、换鞋凳和挂钩把垂直空间利用起来，鞋子、包和钥匙各有位置。', '玄关收纳的三个实用细节', 1, 13, 2, 0, 126, DATE_SUB(NOW(), INTERVAL 13 DAY), DATE_SUB(NOW(), INTERVAL 13 DAY), DATE_SUB(NOW(), INTERVAL 13 DAY), 0),
('早八通勤的 10 分钟早餐', '提前一晚准备好食材，早上只做加热和组合。燕麦、鸡蛋和水果可以轮换，既快又不单调。', '适合上班族的快手早餐', 4, 13, 2, 0, 98, DATE_SUB(NOW(), INTERVAL 11 DAY), DATE_SUB(NOW(), INTERVAL 11 DAY), DATE_SUB(NOW(), INTERVAL 11 DAY), 0),
('桌面收纳：让工作区清爽一点', '显示器支架、理线槽和抽屉分隔盒是我最满意的三样东西，桌面露出来的面积越大越容易保持整洁。', '桌面收纳好物分享', 3, 13, 2, 0, 77, DATE_SUB(NOW(), INTERVAL 9 DAY), DATE_SUB(NOW(), INTERVAL 9 DAY), DATE_SUB(NOW(), INTERVAL 9 DAY), 0),
('换季衣柜整理的顺序', '先全部拿出来，再按当季频率分区，最后用统一衣架和收纳箱收尾。不要一上来就买收纳工具。', '换季衣柜整理步骤', 1, 13, 2, 0, 154, DATE_SUB(NOW(), INTERVAL 7 DAY), DATE_SUB(NOW(), INTERVAL 7 DAY), DATE_SUB(NOW(), INTERVAL 7 DAY), 0),
('周末去郊区走走：轻量行李清单', '一日往返不需要大箱子。证件、充电宝、防晒、雨具和一件薄外套就够了，背双肩包最方便。', '周末短途出行清单', 4, 13, 2, 0, 61, DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 5 DAY), 0),
('敏感肌换季护肤的减法', '换季时先减少叠加步骤，保留温和清洁、保湿和防晒。新产品一次只加一个，观察几天再加下一个。', '换季护肤做减法', 2, 13, 2, 0, 203, DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY), 0),
('租房也能做的低成本软装', '不动硬装，用灯光、地毯、抱枕和一幅画改变氛围。先定一个主色，再选两件呼应的小物。', '租房软装思路', 1, 13, 2, 0, 88, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), 0),
('通勤包里到底该放什么', '按每天必用、偶尔用、应急三层来装。每周清一次包，能减少很多不必要的重量。', '通勤包收纳方法', 5, 13, 2, 0, 45, NOW(), NOW(), NOW(), 0);

-- creator4：阶段更新型，4 篇集中在部分日期
INSERT INTO biz_article (title, content, summary, category_id, author_id, status, risk_level, view_count, publish_time, create_time, update_time, deleted) VALUES
('新手也能拍好的咖啡拉花', '先从稳定奶泡开始，再练注入位置和手腕高度。每天拍一杯，记录失败原因比盲目练习更有用。', '咖啡拉花入门记录', 4, 14, 2, 0, 112, DATE_SUB(NOW(), INTERVAL 12 DAY), DATE_SUB(NOW(), INTERVAL 12 DAY), DATE_SUB(NOW(), INTERVAL 12 DAY), 0),
('一本书读完怎么做笔记', '我会先写三句话摘要，再摘两条能立刻用上的方法，最后留一页写反对意见。笔记不是抄书。', '读书笔记模板分享', 5, 14, 2, 0, 89, DATE_SUB(NOW(), INTERVAL 8 DAY), DATE_SUB(NOW(), INTERVAL 8 DAY), DATE_SUB(NOW(), INTERVAL 8 DAY), 0),
('阳台种香草的第一周', '薄荷和罗勒都长得很快，关键是别急着浇水。土面干了再浇，给足光照，第一周不要施肥。', '阳台香草种植记录', 1, 14, 2, 0, 67, DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY), 0),
('周末做一锅番茄炖牛腩', '牛腩先焯水，番茄分两次放：一次炒出汤底，一次在收尾时保留果肉口感。小火慢炖一个半小时。', '家常番茄炖牛腩做法', 4, 14, 2, 0, 143, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY), 0);

-- creator5：新账号，只有 2 篇
INSERT INTO biz_article (title, content, summary, category_id, author_id, status, risk_level, view_count, publish_time, create_time, update_time, deleted) VALUES
('第一次做播客要准备什么', '一支能用的麦克风、安静的房间和一份提纲就够了。先录三期再决定要不要升级设备。', '播客新手设备清单', 3, 15, 2, 0, 36, DATE_SUB(NOW(), INTERVAL 6 DAY), DATE_SUB(NOW(), INTERVAL 6 DAY), DATE_SUB(NOW(), INTERVAL 6 DAY), 0),
('下班后快速恢复精力的小习惯', '到家先洗澡换衣服，再做十分钟拉伸，最后才打开手机。把工作和休息用一个动作隔开。', '下班后的恢复习惯', 5, 15, 2, 0, 52, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), 0);

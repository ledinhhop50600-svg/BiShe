-- 阶段 0：最小链路验证用的临时表
-- 说明：仅用于验证「前端 → 后端 → MySQL」链路是否打通；阶段 1 设计正式表结构时会删除本表。

CREATE TABLE IF NOT EXISTS demo_ping (
    id      BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    message VARCHAR(255) NOT NULL COMMENT '消息内容',
    PRIMARY KEY (id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT = '链路验证临时表';

INSERT INTO demo_ping (message)
SELECT '链路已打通：这条数据来自 MySQL'
WHERE NOT EXISTS (SELECT 1 FROM demo_ping);

INSERT INTO demo_ping (message)
SELECT 'Spring Boot 4.1.1 + MyBatis-Plus 3.5.17 + MySQL 8.0.46 协同工作正常'
WHERE (SELECT COUNT(*) FROM demo_ping) < 2;

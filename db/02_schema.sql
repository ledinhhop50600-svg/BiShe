-- ================================================================
-- 阶段 1：正式表结构
--
-- 执行方式（注意必须指定客户端字符集，否则中文会乱码）：
--   mysql -u zimeiti -p zimeiti --default-character-set=utf8mb4 < db/02_schema.sql
--
-- 设计原则：
--   1. 全部使用 InnoDB + utf8mb4（支持 emoji，稿件正文里会有）
--   2. 每张表都有注释，每个字段都有注释 —— 答辩时要能逐张讲清"存什么"
--   3. 业务主表用 deleted 字段做逻辑删除（数据不真删，便于追溯与审计）
--   4. 审核相关的表在本阶段就建好（D-A4 的预埋约束），避免后期改表返工
--
-- 表分组：
--   sys_*    系统与权限：sys_user / sys_role / sys_menu / sys_user_role / sys_role_menu
--   biz_*    业务内容　：biz_category / biz_tag / biz_article / biz_article_tag / biz_report
--   audit_*  审核与适配：audit_platform / audit_rule / audit_record / audit_review
--                       audit_sensitive_word / audit_adaptation
-- ================================================================

SET NAMES utf8mb4;

-- 阶段 0 的临时验证表，本阶段正式表结构启用后删除
DROP TABLE IF EXISTS demo_ping;

-- ================================================================
-- 一、系统与权限（sys_*）
-- ================================================================

DROP TABLE IF EXISTS sys_user_role;
DROP TABLE IF EXISTS sys_role_menu;
DROP TABLE IF EXISTS sys_menu;
DROP TABLE IF EXISTS sys_user;
DROP TABLE IF EXISTS sys_role;

-- 用户表：系统的三种角色（超级管理员 / 审核员 / 创作者）共用这一张表，靠角色关联区分
CREATE TABLE sys_user (
    id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    username    VARCHAR(50)  NOT NULL COMMENT '登录账号',
    password    VARCHAR(100) NOT NULL COMMENT '密码（BCrypt 加盐哈希，不可逆；数据库里看不到明文）',
    nickname    VARCHAR(50)  NOT NULL COMMENT '昵称（界面上显示的名字）',
    avatar      VARCHAR(255) DEFAULT NULL COMMENT '头像地址',
    email       VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    phone       VARCHAR(20)  DEFAULT NULL COMMENT '手机号',
    status      TINYINT      NOT NULL DEFAULT 1 COMMENT '账号状态：1 启用，0 禁用（禁用后无法登录）',
    remark      VARCHAR(255) DEFAULT NULL COMMENT '备注',
    create_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted     TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0 正常，1 已删除',
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='用户表';

-- 角色表
CREATE TABLE sys_role (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    role_name   VARCHAR(50) NOT NULL COMMENT '角色名称：超级管理员 / 审核员 / 创作者',
    role_key    VARCHAR(50) NOT NULL COMMENT '角色标识（程序里用）：admin / reviewer / creator',
    description VARCHAR(255) DEFAULT NULL COMMENT '角色说明',
    sort        INT         NOT NULL DEFAULT 0 COMMENT '显示排序（越小越前）',
    status      TINYINT     NOT NULL DEFAULT 1 COMMENT '状态：1 启用，0 禁用',
    create_time DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted     TINYINT     NOT NULL DEFAULT 0 COMMENT '逻辑删除：0 正常，1 已删除',
    PRIMARY KEY (id),
    UNIQUE KEY uk_role_key (role_key)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='角色表';

-- 菜单表：同时保存"界面菜单"和"按钮权限"，靠 menu_type 区分
CREATE TABLE sys_menu (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    parent_id   BIGINT      NOT NULL DEFAULT 0 COMMENT '上级菜单 id，0 表示顶级',
    menu_name   VARCHAR(50) NOT NULL COMMENT '菜单名称（界面上显示的文字）',
    menu_type   CHAR(1)     NOT NULL COMMENT '类型：M 目录，C 菜单页面，F 按钮权限',
    path        VARCHAR(200) DEFAULT NULL COMMENT '前端路由地址',
    component   VARCHAR(200) DEFAULT NULL COMMENT '前端组件路径',
    perms       VARCHAR(100) DEFAULT NULL COMMENT '权限标识，如 article:add；后端接口用它校验权限',
    icon        VARCHAR(50)  DEFAULT NULL COMMENT '图标名称',
    sort        INT         NOT NULL DEFAULT 0 COMMENT '显示排序',
    visible     TINYINT     NOT NULL DEFAULT 1 COMMENT '是否显示：1 显示，0 隐藏',
    status      TINYINT     NOT NULL DEFAULT 1 COMMENT '状态：1 启用，0 禁用',
    create_time DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_parent_id (parent_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='菜单与按钮权限表';

-- 用户-角色关联表：一个用户可以有多个角色（本项目里每类角色各一人，但结构上一对多）
CREATE TABLE sys_user_role (
    id      BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
    user_id BIGINT NOT NULL COMMENT '用户 id',
    role_id BIGINT NOT NULL COMMENT '角色 id',
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_role (user_id, role_id),
    KEY idx_role_id (role_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='用户角色关联表';

-- 角色-菜单关联表：决定"这个角色能看到哪些菜单、能点哪些按钮"
CREATE TABLE sys_role_menu (
    id      BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
    role_id BIGINT NOT NULL COMMENT '角色 id',
    menu_id BIGINT NOT NULL COMMENT '菜单 id',
    PRIMARY KEY (id),
    UNIQUE KEY uk_role_menu (role_id, menu_id),
    KEY idx_menu_id (menu_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='角色菜单关联表';

-- ================================================================
-- 二、业务内容（biz_*）
-- ================================================================

DROP TABLE IF EXISTS biz_article_tag;
DROP TABLE IF EXISTS biz_article;
DROP TABLE IF EXISTS biz_tag;
DROP TABLE IF EXISTS biz_category;
DROP TABLE IF EXISTS biz_report;

-- 稿件分类
CREATE TABLE biz_category (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    name        VARCHAR(50) NOT NULL COMMENT '分类名称，如 生活家居 / 美妆护肤',
    sort        INT         NOT NULL DEFAULT 0 COMMENT '显示排序',
    status      TINYINT     NOT NULL DEFAULT 1 COMMENT '状态：1 启用，0 停用',
    create_time DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='稿件分类表';

-- 稿件标签（一篇文章可打多个标签）
CREATE TABLE biz_tag (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    name        VARCHAR(30) NOT NULL COMMENT '标签名，如 收纳 / 小户型',
    create_time DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_name (name)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='稿件标签表';

-- 稿件主表：整个系统的核心业务对象，也是智能体的审核对象
CREATE TABLE biz_article (
    id            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    title         VARCHAR(200) NOT NULL COMMENT '标题',
    content       LONGTEXT     NOT NULL COMMENT '正文内容（智能体审核的就是这个字段）',
    summary       VARCHAR(500)  DEFAULT NULL COMMENT '摘要',
    cover_image   VARCHAR(255)  DEFAULT NULL COMMENT '封面图地址',
    category_id   BIGINT        DEFAULT NULL COMMENT '分类 id',
    author_id     BIGINT       NOT NULL COMMENT '作者（创作者）用户 id',
    status        TINYINT      NOT NULL DEFAULT 0 COMMENT '稿件状态：0 草稿，1 待审核，2 已发布，3 已驳回，4 已阻断，5 已下架',
    risk_level    TINYINT      NOT NULL DEFAULT -1 COMMENT '当前风险等级（智能体判定结果）：-1 未判定，0 通过，1 疑似，2 违规，3 严重',
    reject_reason VARCHAR(1000) DEFAULT NULL COMMENT '驳回/阻断原因（含违规片段与修改建议，展示给创作者）',
    publish_time  DATETIME      DEFAULT NULL COMMENT '发布时间（状态变为已发布时写入）',
    view_count    INT          NOT NULL DEFAULT 0 COMMENT '阅读量（演示用，可手动累加）',
    create_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted       TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0 正常，1 已删除',
    PRIMARY KEY (id),
    KEY idx_author (author_id),
    KEY idx_status (status),
    KEY idx_category (category_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='稿件表';

-- 稿件-标签关联表
CREATE TABLE biz_article_tag (
    id         BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
    article_id BIGINT NOT NULL COMMENT '稿件 id',
    tag_id     BIGINT NOT NULL COMMENT '标签 id',
    PRIMARY KEY (id),
    UNIQUE KEY uk_article_tag (article_id, tag_id),
    KEY idx_tag (tag_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='稿件标签关联表';

-- 举报表：创作者举报已发布稿件，审核员处理
CREATE TABLE biz_report (
    id            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    article_id    BIGINT       NOT NULL COMMENT '被举报的稿件 id',
    reporter_id   BIGINT       NOT NULL COMMENT '举报人用户 id',
    reason        VARCHAR(500) NOT NULL COMMENT '举报理由（举报人填写）',
    status        TINYINT      NOT NULL DEFAULT 0 COMMENT '处理状态：0 待处理，1 举报成立，2 举报不成立',
    handler_id    BIGINT        DEFAULT NULL COMMENT '处理人（审核员）用户 id',
    handle_remark VARCHAR(500)  DEFAULT NULL COMMENT '处理意见',
    handle_time   DATETIME      DEFAULT NULL COMMENT '处理时间',
    create_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '举报时间',
    PRIMARY KEY (id),
    KEY idx_article (article_id),
    KEY idx_status (status)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='举报表';

-- ================================================================
-- 三、审核与适配（audit_*）—— 为智能体预埋，本阶段只建表不使用
-- ================================================================

DROP TABLE IF EXISTS audit_adaptation;
DROP TABLE IF EXISTS audit_review;
DROP TABLE IF EXISTS audit_record;
DROP TABLE IF EXISTS audit_rule;
DROP TABLE IF EXISTS audit_sensitive_word;
DROP TABLE IF EXISTS audit_platform;

-- 目标平台清单：智能体做"按平台规则审核"和"跨平台内容适配"的依据
CREATE TABLE audit_platform (
    id             BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    platform_key   VARCHAR(50) NOT NULL COMMENT '平台标识：wechat / xiaohongshu / weibo / bilibili / douyin',
    platform_name  VARCHAR(50) NOT NULL COMMENT '平台名称：微信公众号 / 小红书 / 微博 / B站 / 抖音',
    title_max_len  INT         NOT NULL DEFAULT 30 COMMENT '标题字数上限（格式约束）',
    content_max_len INT        NOT NULL DEFAULT 1000 COMMENT '正文字数上限（格式约束）',
    tag_rule       VARCHAR(200) DEFAULT NULL COMMENT '话题标签规则描述，如"以#开头，建议 3-5 个"',
    style_desc     VARCHAR(500) DEFAULT NULL COMMENT '内容风格要求，如"口语化、多 emoji、面向年轻女性"',
    sort           INT         NOT NULL DEFAULT 0 COMMENT '显示排序',
    status         TINYINT     NOT NULL DEFAULT 1 COMMENT '状态：1 启用，0 停用',
    create_time    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_platform_key (platform_key)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='目标平台清单与格式约束表（约束数值以各平台公开创作规范为准）';

-- 审核规则库：智能体做 RAG 检索的知识来源；platform_id 为空表示"通用规则"，适用于所有平台
CREATE TABLE audit_rule (
    id                 BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    rule_code          VARCHAR(30)  NOT NULL COMMENT '规则编号，如 AD-003（判定理由里会引用它，便于追溯到规则）',
    rule_name          VARCHAR(100) NOT NULL COMMENT '规则名称，如"绝对化用语"',
    category           VARCHAR(30)  NOT NULL COMMENT '规则类别：广告法 / 虚假宣传 / 低俗擦边 / 引流诱导 / 违禁品 / 侵权',
    platform_id        BIGINT        DEFAULT NULL COMMENT '适用平台 id；为空表示通用规则（所有平台都适用）',
    rule_content       VARCHAR(1000) NOT NULL COMMENT '规则内容描述（喂给智能体的规则文本）',
    source             VARCHAR(300)  DEFAULT NULL COMMENT '规则来源（法规/规范名称与条款，答辩要能溯源）',
    suggested_level    TINYINT      NOT NULL DEFAULT 2 COMMENT '命中后建议的风险等级：0 通过，1 疑似，2 违规，3 严重',
    enabled            TINYINT      NOT NULL DEFAULT 1 COMMENT '是否启用：1 启用，0 停用',
    create_time        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_rule_code (rule_code),
    KEY idx_category (category),
    KEY idx_platform (platform_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='审核规则库（通用规则 + 平台专属规则）';

-- 审核记录表：每一次智能体判定都留一条，作为评测数据与追溯依据
CREATE TABLE audit_record (
    id                  BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    article_id          BIGINT       NOT NULL COMMENT '被审核的稿件 id',
    trigger_type        TINYINT      NOT NULL COMMENT '触发场景：1 发布前预检，2 发布后审核，3 举报复审，4 适配后平台预检',
    platform_id         BIGINT        DEFAULT NULL COMMENT '目标平台 id（按平台规则审核时记录；本平台审核为空）',
    risk_level          TINYINT      NOT NULL COMMENT '智能体判定的风险等级：0 通过，1 疑似，2 违规，3 严重',
    reason              TEXT         COMMENT '判定理由（智能体生成的说明文字）',
    hit_rule_codes      VARCHAR(300)  DEFAULT NULL COMMENT '命中的规则编号，多个用逗号分隔，如 AD-003,FB-011',
    violation_fragments TEXT         COMMENT '违规片段（JSON 数组字符串，用于界面高亮与展示给创作者）',
    content_hash        VARCHAR(64)   DEFAULT NULL COMMENT '判定时稿件标题+正文的 SHA-256；内容改过则本记录视为过期',
    suggestion          TEXT         COMMENT '处置建议与修改建议（反馈给创作者的具体改法）',
    model_name          VARCHAR(50)   DEFAULT NULL COMMENT '使用的模型，如 deepseek-flash（对比实验需要）',
    prompt_tokens       INT          NOT NULL DEFAULT 0 COMMENT '本次调用消耗的输入 token 数（成本统计）',
    completion_tokens   INT          NOT NULL DEFAULT 0 COMMENT '本次调用消耗的输出 token 数（成本统计）',
    duration_ms         INT          NOT NULL DEFAULT 0 COMMENT '本次判定耗时（毫秒）',
    create_time         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '判定时间',
    PRIMARY KEY (id),
    KEY idx_article (article_id),
    KEY idx_trigger (trigger_type)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='智能体审核记录表（每次判定留痕，用于评测与追溯）';

-- 审核复核/改判记录：审核员的处理动作，同时是人机协同的标注数据来源（D-A7）
CREATE TABLE audit_review (
    id              BIGINT        NOT NULL AUTO_INCREMENT COMMENT '主键',
    audit_record_id BIGINT        NOT NULL COMMENT '对应的智能体审核记录 id',
    article_id      BIGINT        NOT NULL COMMENT '稿件 id（冗余字段，便于直接查询）',
    reviewer_id     BIGINT        NOT NULL COMMENT '审核员用户 id',
    action          TINYINT       NOT NULL COMMENT '处理动作：1 采纳智能体建议，2 改判，3 驳回',
    final_level     TINYINT       NOT NULL COMMENT '审核员给出的最终风险等级：0 通过，1 疑似，2 违规，3 严重',
    remark          VARCHAR(1000)  DEFAULT NULL COMMENT '改判原因/处理意见（改判时必填，作为真实标注数据留存）',
    create_time     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '处理时间',
    PRIMARY KEY (id),
    KEY idx_audit_record (audit_record_id),
    KEY idx_article (article_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='审核复核与改判记录表（人机协同 + 评测标注数据来源）';

-- 敏感词库：传统方案，论文里的对比基线（关键词规则 vs 纯大模型 vs RAG+大模型）
CREATE TABLE audit_sensitive_word (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    word        VARCHAR(100) NOT NULL COMMENT '敏感词',
    category    VARCHAR(30) NOT NULL COMMENT '所属类别（与规则类别保持一致，便于对比）',
    level       TINYINT     NOT NULL DEFAULT 2 COMMENT '命中后的处理等级：1 疑似，2 违规，3 严重',
    enabled     TINYINT     NOT NULL DEFAULT 1 COMMENT '是否启用：1 启用，0 停用',
    create_time DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_word (word)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='敏感词库（传统关键词匹配方案，作为论文对比基线）';

-- 适配记录表：一次跨平台适配的产物与自检结果
CREATE TABLE audit_adaptation (
    id                 BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    article_id         BIGINT       NOT NULL COMMENT '源稿件 id',
    platform_id        BIGINT       NOT NULL COMMENT '目标平台 id',
    adapted_title      VARCHAR(300)  DEFAULT NULL COMMENT '适配后的标题',
    adapted_content    LONGTEXT      DEFAULT NULL COMMENT '适配后的正文',
    adapted_tags       VARCHAR(300)  DEFAULT NULL COMMENT '适配后的话题标签',
    format_check       VARCHAR(1000) DEFAULT NULL COMMENT '格式自检结果，如"标题 18/20 字，标签 3 个，通过"',
    compliance_check   VARCHAR(1000) DEFAULT NULL COMMENT '该平台的合规预检结论',
    version            INT          NOT NULL DEFAULT 1 COMMENT '同一稿件的第几次适配（同一平台每生成一次 +1，便于回看历史版本）',
    adapted_by         BIGINT        DEFAULT NULL COMMENT '操作人用户 id',
    create_time        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '适配时间',
    PRIMARY KEY (id),
    KEY idx_article (article_id),
    KEY idx_platform (platform_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='跨平台内容适配记录表';

-- ================================================================
-- 建表完成。核对：共 16 张表
--   sys_user, sys_role, sys_menu, sys_user_role, sys_role_menu,
--   biz_category, biz_tag, biz_article, biz_article_tag, biz_report,
--   audit_platform, audit_rule, audit_record, audit_review,
--   audit_sensitive_word, audit_adaptation
-- ================================================================
SELECT COUNT(*) AS 本库表数量
FROM information_schema.tables
WHERE table_schema = 'zimeiti';

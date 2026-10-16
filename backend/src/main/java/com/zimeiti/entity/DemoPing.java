package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 链路验证用的实体，对应数据库 demo_ping 表。
 * <p>仅用于阶段 0 验证「前端 → 后端 → MySQL」链路；阶段 1 设计正式表结构时删除。
 * <p>注意：类名 DemoPing 与表名 demo_ping 的对应关系由 @TableName 显式声明，
 * 属性 message 与字段 message 同名，靠 application.properties 里的驼峰转换配置处理下划线命名。
 */
@Data
@TableName("demo_ping")
public class DemoPing {

    /** 主键，数据库自增 */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 消息内容 */
    private String message;
}

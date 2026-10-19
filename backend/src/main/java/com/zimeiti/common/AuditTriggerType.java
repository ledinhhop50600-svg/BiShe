package com.zimeiti.common;

/**
 * 审核触发场景。契约用字符串（PRE_CHECK 等），数据库用数字（1-4）。
 * <p>集中在这里做映射，避免各处散落 `if ("POST_AUDIT".equals(...))` 与魔法数字。
 */
public enum AuditTriggerType {

    PRE_CHECK(1, "发布前预检"),
    POST_AUDIT(2, "发布审核"),
    REPORT_REVIEW(3, "举报复审"),
    ADAPT_CHECK(4, "适配预检");

    private final int code;
    private final String text;

    AuditTriggerType(int code, String text) {
        this.code = code;
        this.text = text;
    }

    public int code() {
        return code;
    }

    public String text() {
        return text;
    }

    /** 契约字符串 -> 枚举；未知值按"发布审核"处理，避免把脏参数写成预检 */
    public static AuditTriggerType of(String contract) {
        if (contract == null) {
            return POST_AUDIT;
        }
        return switch (contract) {
            case "PRE_CHECK" -> PRE_CHECK;
            case "REPORT_REVIEW" -> REPORT_REVIEW;
            case "ADAPT_CHECK" -> ADAPT_CHECK;
            default -> POST_AUDIT;
        };
    }

    public static String textOf(Integer code) {
        if (code == null) {
            return "未知";
        }
        for (AuditTriggerType t : values()) {
            if (t.code == code) {
                return t.text;
            }
        }
        return "未知";
    }
}

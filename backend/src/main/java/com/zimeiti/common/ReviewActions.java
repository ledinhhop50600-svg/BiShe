package com.zimeiti.common;

/**
 * 审核员的处理动作（audit_review.action）。
 */
public final class ReviewActions {

    /** 采纳智能体建议 */
    public static final int ADOPT = 1;
    /** 改判：结论与智能体建议不一致，原因必填 */
    public static final int OVERRIDE = 2;
    /** 人工判定：没有可用的智能体初判（未运行 / 失败 / 内容已修改） */
    public static final int MANUAL = 3;

    private ReviewActions() {
    }

    public static String text(Integer action) {
        if (action == null) {
            return "未知";
        }
        return switch (action) {
            case ADOPT -> "采纳";
            case OVERRIDE -> "改判";
            case MANUAL -> "人工判定";
            default -> "未知";
        };
    }
}

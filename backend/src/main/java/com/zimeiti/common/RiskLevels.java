package com.zimeiti.common;

/**
 * 风险等级的显示文案（与前端 articleStatus.js 的字典保持一致）。
 */
public final class RiskLevels {

    private RiskLevels() {
    }

    public static String text(Integer level) {
        if (level == null) {
            return "未判定";
        }
        return switch (level) {
            case 0 -> "通过";
            case 1 -> "疑似";
            case 2 -> "违规";
            case 3 -> "严重";
            default -> "未判定";
        };
    }
}

package com.zimeiti.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 适配记录返回对象。
 * <p>比实体多了平台标识与名称（前端直接显示），标签从空格分隔的字符串还原成数组。
 */
@Data
public class AdaptationVO {

    private Long id;

    private Long articleId;

    private String platformKey;

    private String platformName;

    /** 同一稿件在同一平台的第几次适配 */
    private Integer version;

    private String title;

    private String content;

    private List<String> tags;

    /** 格式自检摘要（通过 / 未通过 + 字数标签 + 问题） */
    private String formatCheck;

    /** 合规预检摘要（等级 + 理由 + 命中规则） */
    private String complianceCheck;

    private LocalDateTime createTime;
}

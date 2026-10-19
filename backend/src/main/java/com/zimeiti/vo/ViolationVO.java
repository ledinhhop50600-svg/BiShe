package com.zimeiti.vo;

import lombok.Data;

/**
 * 违规片段（来自智能体结论）。
 */
@Data
public class ViolationVO {

    private String fragment;

    private String issue;

    private String suggestion;
}

package com.zimeiti.service;

import com.zimeiti.common.PageResult;
import com.zimeiti.dto.ReportHandleDTO;
import com.zimeiti.vo.ReportVO;

import java.util.Map;

/**
 * 举报服务。
 */
public interface ReportService {

    /** 举报列表（管理员/审核员） */
    PageResult<ReportVO> page(long current, long size, Integer status);

    /** 创作者举报一篇已发布的稿件 */
    void create(Long articleId, String reason);

    /** 审核员处理举报：成立则稿件下架，不成立则驳回举报 */
    void handle(Long id, ReportHandleDTO dto);

    /** 对举报稿件运行一次智能体复审（REPORT_REVIEW，落审核记录） */
    Map<String, Object> agentReview(Long id);
}

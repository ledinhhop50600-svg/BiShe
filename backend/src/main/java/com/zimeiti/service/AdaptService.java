package com.zimeiti.service;

import com.zimeiti.vo.AdaptationVO;

import java.util.List;
import java.util.Map;

/**
 * 跨平台内容适配服务。
 */
public interface AdaptService {

    /**
     * 对一篇稿件生成多个平台的适配版本，并把每个平台的结果落库。
     *
     * @return 智能体按契约返回的结果；智能体不可用时返回带 agentFailed=true 的降级结果
     */
    Map<String, Object> adapt(Long articleId, List<String> platformKeys);

    /** 某篇稿件的适配历史（按时间倒序） */
    List<AdaptationVO> listByArticle(Long articleId);
}

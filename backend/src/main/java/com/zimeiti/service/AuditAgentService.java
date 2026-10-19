package com.zimeiti.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.BizException;
import com.zimeiti.entity.AuditPlatform;
import com.zimeiti.entity.AuditRule;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.mapper.AuditPlatformMapper;
import com.zimeiti.mapper.AuditRuleMapper;
import com.zimeiti.mapper.BizArticleMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 审核智能体服务：把"主系统里的数据"组装成契约请求，交给智能体，再把结果带回来。
 * <p>它承担三件职责：
 *  1. **组装上下文**：稿件内容 + 目标平台约束 + 本次可用规则（智能体不连数据库，上下文必须由这里给齐）；
 *  2. **降级**：智能体不可用时不阻断业务，返回带 {@code agentFailed=true} 的结果，由界面提示转人工；
 *  3. **统一出口**：阶段 5/6 的预检、举报复审都走这个方法，只是 triggerType 不同。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuditAgentService {

    private static final String LOCAL_PLATFORM_KEY = "local";

    private final BizArticleMapper articleMapper;
    private final AuditRuleMapper ruleMapper;
    private final AuditPlatformMapper platformMapper;
    private final AgentClient agentClient;

    /**
     * 对一篇稿件调用智能体审核。
     *
     * @param triggerType 契约里的触发场景：POST_AUDIT / PRE_CHECK / REPORT_REVIEW
     */
    public Map<String, Object> audit(Long articleId, String triggerType) {
        BizArticle article = articleMapper.selectById(articleId);
        if (article == null) {
            throw new BizException("稿件不存在");
        }

        AuditPlatform platform = platformMapper.selectOne(
                Wrappers.<AuditPlatform>lambdaQuery().eq(AuditPlatform::getPlatformKey, LOCAL_PLATFORM_KEY));

        // 本次可用规则 = 通用规则（platform_id 为空）+ 该平台的专属规则，且只取启用的
        Long platformId = platform == null ? null : platform.getId();
        List<AuditRule> rules = ruleMapper.selectList(Wrappers.<AuditRule>lambdaQuery()
                .eq(AuditRule::getEnabled, 1)
                .and(w -> {
                    w.isNull(AuditRule::getPlatformId);
                    if (platformId != null) {
                        w.or().eq(AuditRule::getPlatformId, platformId);
                    }
                })
                .orderByAsc(AuditRule::getId));

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("requestId", UUID.randomUUID().toString());
        request.put("articleId", article.getId());
        request.put("triggerType", triggerType);
        request.put("targetPlatformKey", LOCAL_PLATFORM_KEY);
        request.put("title", article.getTitle());
        request.put("content", article.getContent() == null ? "" : article.getContent());
        request.put("platform", toPlatformMap(platform));
        request.put("rules", toRuleList(rules));

        try {
            return agentClient.audit(request);
        } catch (AgentClient.AgentUnavailableException e) {
            // 降级：不抛异常、不阻断业务，把"智能体不可用"如实告诉界面
            log.warn("智能体不可用，已降级为人工审核：{}", e.getMessage());
            Map<String, Object> degraded = new LinkedHashMap<>();
            degraded.put("agentFailed", true);
            degraded.put("error", e.getMessage());
            degraded.put("message", "智能体服务不可用，请改为人工审核");
            return degraded;
        }
    }

    private Map<String, Object> toPlatformMap(AuditPlatform p) {
        if (p == null) {
            return null;
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("platformKey", p.getPlatformKey());
        m.put("platformName", p.getPlatformName());
        m.put("titleMaxLen", p.getTitleMaxLen());
        m.put("contentMaxLen", p.getContentMaxLen());
        m.put("tagRule", p.getTagRule());
        m.put("styleDesc", p.getStyleDesc());
        return m;
    }

    private List<Map<String, Object>> toRuleList(List<AuditRule> rules) {
        List<Map<String, Object>> list = new ArrayList<>();
        for (AuditRule r : rules) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("code", r.getRuleCode());
            m.put("name", r.getRuleName());
            m.put("category", r.getCategory());
            m.put("content", r.getRuleContent());
            m.put("source", r.getSource());
            m.put("suggestedLevel", r.getSuggestedLevel());
            list.add(m);
        }
        return list;
    }
}

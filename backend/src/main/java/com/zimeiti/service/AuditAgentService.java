package com.zimeiti.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.AuditTriggerType;
import com.zimeiti.common.BizException;
import com.zimeiti.common.ContentHash;
import com.zimeiti.entity.AuditPlatform;
import com.zimeiti.entity.AuditRule;
import com.zimeiti.entity.AuditSensitiveWord;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.mapper.AuditPlatformMapper;
import com.zimeiti.mapper.AuditRuleMapper;
import com.zimeiti.mapper.AuditSensitiveWordMapper;
import com.zimeiti.mapper.BizArticleMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

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
 *  3. **统一出口**：正式审核、发布前预检都走这里，只是 triggerType 与是否落库不同。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuditAgentService {

    private static final String LOCAL_PLATFORM_KEY = "local";

    private final BizArticleMapper articleMapper;
    private final AuditRuleMapper ruleMapper;
    private final AuditPlatformMapper platformMapper;
    private final AuditSensitiveWordMapper wordMapper;
    private final AgentClient agentClient;
    private final AuditRecordService auditRecordService;

    /**
     * 对一篇已存在的稿件调用智能体审核。
     *
     * @param triggerType 契约里的触发场景：POST_AUDIT / PRE_CHECK / REPORT_REVIEW
     */
    public Map<String, Object> audit(Long articleId, String triggerType) {
        BizArticle article = articleMapper.selectById(articleId);
        if (article == null) {
            throw new BizException("稿件不存在");
        }

        Map<String, Object> request = buildRequest(article.getId(), article.getTitle(),
                article.getContent(), triggerType);
        String contentHash = ContentHash.of(article.getTitle(), article.getContent());

        try {
            Map<String, Object> result = agentClient.audit(request);
            // 正式审核（POST_AUDIT）必须留痕；发布前预检只是给创作者的提示，不写入审核记录，
            // 否则每点一次"预检"就多一条记录，会污染工作台与统计。
            if (AuditTriggerType.of(triggerType) == AuditTriggerType.POST_AUDIT) {
                Long recordId = auditRecordService.saveAgentResult(
                        article.getId(), triggerType, null, contentHash, result, false, null);
                result.put("auditRecordId", recordId);
            }
            return result;
        } catch (AgentClient.AgentUnavailableException e) {
            log.warn("智能体不可用，已降级为人工审核：{}", e.getMessage());
            Map<String, Object> degraded = degraded(e.getMessage(), "智能体服务不可用，请改为人工审核");
            if (AuditTriggerType.of(triggerType) == AuditTriggerType.POST_AUDIT) {
                Long recordId = auditRecordService.saveAgentResult(
                        article.getId(), triggerType, null, contentHash, Map.of(), true, e.getMessage());
                degraded.put("auditRecordId", recordId);
            }
            return degraded;
        }
    }

    /**
     * 发布前预检：不要求稿件已保存，不落库，只给创作者提示。
     * <p>为什么单独提供：创作者常常先写一段就想看看风险，此时还没有稿件 id；
     * 若先存草稿再预检，会把用户的编辑动作变成一次保存（已发布稿件还会触发重审），体验不对。
     */
    public Map<String, Object> precheck(String title, String content) {
        if (!StringUtils.hasText(title) && !StringUtils.hasText(content)) {
            throw new BizException(400, "请先填写标题或正文");
        }
        Map<String, Object> request = buildRequest(0L, title, content, "PRE_CHECK");
        try {
            return agentClient.audit(request);
        } catch (AgentClient.AgentUnavailableException e) {
            log.warn("预检时智能体不可用：{}", e.getMessage());
            return degraded(e.getMessage(), "智能体服务不可用，请先按敏感词提示自查");
        }
    }

    /**
     * 组装契约请求：本地平台约束 + 本次可用规则（通用 + 本平台专属）+ 敏感词。
     * 智能体不连数据库，这些上下文必须由主系统给齐。
     */
    private Map<String, Object> buildRequest(Long articleId, String title, String content,
                                             String triggerType) {
        AuditPlatform platform = platformMapper.selectOne(
                Wrappers.<AuditPlatform>lambdaQuery().eq(AuditPlatform::getPlatformKey, LOCAL_PLATFORM_KEY));

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
        request.put("articleId", articleId);
        request.put("triggerType", triggerType);
        request.put("targetPlatformKey", LOCAL_PLATFORM_KEY);
        request.put("title", title == null ? "" : title);
        request.put("content", content == null ? "" : content);
        request.put("platform", toPlatformMap(platform));
        request.put("rules", toRuleList(rules));
        // 敏感词库随请求下发：智能体用它做"词面兜底"的关键词来源。
        // 规则里的示例词常是完整短语，正文写法常有出入；短词（"加我微信"）能兜住这种情况。
        request.put("sensitiveWords", toWordList());
        return request;
    }

    private Map<String, Object> degraded(String error, String message) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("agentFailed", true);
        out.put("error", error);
        out.put("message", message);
        return out;
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

    /** 启用的敏感词，作为智能体的词面关键词来源 */
    private List<Map<String, Object>> toWordList() {
        List<Map<String, Object>> list = new ArrayList<>();
        for (AuditSensitiveWord w : wordMapper.selectList(
                Wrappers.<AuditSensitiveWord>lambdaQuery().eq(AuditSensitiveWord::getEnabled, 1))) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("word", w.getWord());
            m.put("level", w.getLevel());
            m.put("category", w.getCategory());
            list.add(m);
        }
        return list;
    }
}

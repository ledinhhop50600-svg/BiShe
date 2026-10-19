package com.zimeiti.service.impl;

import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.BizException;
import com.zimeiti.entity.AuditAdaptation;
import com.zimeiti.entity.AuditPlatform;
import com.zimeiti.entity.AuditRule;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.mapper.AuditAdaptationMapper;
import com.zimeiti.mapper.AuditPlatformMapper;
import com.zimeiti.mapper.AuditRuleMapper;
import com.zimeiti.mapper.BizArticleMapper;
import com.zimeiti.service.AdaptService;
import com.zimeiti.service.AgentClient;
import com.zimeiti.vo.AdaptationVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 跨平台适配服务实现。
 * <p>职责与审核服务对称：
 *  1. **组装上下文**：稿件正文 + 目标平台约束 + 适用规则（通用规则 + 各平台专属规则）；
 *  2. **落库**：每个平台的结果写一行 audit_adaptation，版本号按"稿件 + 平台"递增；
 *  3. **降级**：智能体不可用时不阻断，返回 agentFailed=true，前端提示稍后重试。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AdaptServiceImpl implements AdaptService {

    private static final String LOCAL_PLATFORM_KEY = "local";
    private static final int MAX_PLATFORMS = 5;

    private final BizArticleMapper articleMapper;
    private final AuditPlatformMapper platformMapper;
    private final AuditRuleMapper ruleMapper;
    private final AuditAdaptationMapper adaptationMapper;
    private final AgentClient agentClient;

    @Override
    public Map<String, Object> adapt(Long articleId, List<String> platformKeys) {
        BizArticle article = mustGet(articleId);
        assertCanAdapt(article);

        List<String> keys = normalizeKeys(platformKeys);
        Map<String, AuditPlatform> platformByKey = loadPlatforms(keys);
        List<AuditPlatform> ordered = keys.stream().map(platformByKey::get).toList();

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("requestId", UUID.randomUUID().toString());
        request.put("articleId", article.getId());
        request.put("title", article.getTitle());
        request.put("content", article.getContent() == null ? "" : article.getContent());
        request.put("targetPlatformKeys", keys);
        request.put("platforms", ordered.stream().map(this::toPlatformMap).toList());
        request.put("rules", toRuleList(loadRules(ordered), ordered));

        Map<String, Object> response;
        try {
            response = agentClient.adapt(request);
        } catch (AgentClient.AgentUnavailableException e) {
            log.warn("智能体适配不可用，已降级：{}", e.getMessage());
            Map<String, Object> degraded = new LinkedHashMap<>();
            degraded.put("agentFailed", true);
            degraded.put("error", e.getMessage());
            degraded.put("message", "智能体服务不可用，请稍后重试；平台较多时可减少目标平台数量");
            return degraded;
        }

        if (!Boolean.TRUE.equals(response.get("agentFailed"))) {
            saveResults(article, response, platformByKey);
        }
        return response;
    }

    @Override
    public List<AdaptationVO> listByArticle(Long articleId) {
        BizArticle article = mustGet(articleId);
        assertCanAdapt(article);

        Map<Long, AuditPlatform> platformById = platformMapper.selectList(null).stream()
                .collect(Collectors.toMap(AuditPlatform::getId, p -> p));
        List<AuditAdaptation> rows = adaptationMapper.selectList(
                Wrappers.<AuditAdaptation>lambdaQuery()
                        .eq(AuditAdaptation::getArticleId, articleId)
                        .orderByDesc(AuditAdaptation::getCreateTime)
                        .orderByDesc(AuditAdaptation::getId));
        return rows.stream().map(row -> toVO(row, platformById.get(row.getPlatformId()))).toList();
    }

    // ------------------------------------------------------------------
    // 上下文组装
    // ------------------------------------------------------------------

    private List<String> normalizeKeys(List<String> platformKeys) {
        List<String> keys = platformKeys == null ? List.of() : platformKeys.stream()
                .filter(StringUtils::hasText)
                .map(String::trim)
                .distinct()
                .toList();
        if (keys.isEmpty()) {
            throw new BizException(400, "请至少选择一个目标平台");
        }
        if (keys.size() > MAX_PLATFORMS) {
            throw new BizException(400, "一次最多适配 " + MAX_PLATFORMS + " 个平台");
        }
        if (keys.contains(LOCAL_PLATFORM_KEY)) {
            throw new BizException(400, "「本平台」不是适配目标，请选择外部平台");
        }
        return keys;
    }

    private Map<String, AuditPlatform> loadPlatforms(List<String> keys) {
        List<AuditPlatform> platforms = platformMapper.selectList(
                Wrappers.<AuditPlatform>lambdaQuery()
                        .in(AuditPlatform::getPlatformKey, keys)
                        .eq(AuditPlatform::getStatus, 1));
        Map<String, AuditPlatform> byKey = platforms.stream()
                .collect(Collectors.toMap(AuditPlatform::getPlatformKey, p -> p));
        List<String> missing = keys.stream().filter(k -> !byKey.containsKey(k)).toList();
        if (!missing.isEmpty()) {
            throw new BizException(400, "目标平台不存在或已停用：" + String.join("、", missing));
        }
        return byKey;
    }

    /** 本次可下发的规则 = 通用规则 + 所选平台的专属规则（只取启用的） */
    private List<AuditRule> loadRules(List<AuditPlatform> platforms) {
        List<Long> platformIds = platforms.stream().map(AuditPlatform::getId).toList();
        return ruleMapper.selectList(Wrappers.<AuditRule>lambdaQuery()
                .eq(AuditRule::getEnabled, 1)
                .and(w -> {
                    w.isNull(AuditRule::getPlatformId);
                    if (!platformIds.isEmpty()) {
                        w.or().in(AuditRule::getPlatformId, platformIds);
                    }
                })
                .orderByAsc(AuditRule::getId));
    }

    private Map<String, Object> toPlatformMap(AuditPlatform p) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("platformKey", p.getPlatformKey());
        m.put("platformName", p.getPlatformName());
        m.put("titleMaxLen", p.getTitleMaxLen());
        m.put("contentMaxLen", p.getContentMaxLen());
        m.put("tagRule", p.getTagRule());
        m.put("styleDesc", p.getStyleDesc());
        return m;
    }

    /**
     * 规则带上 platformKey：智能体一次适配多个平台时，靠它给每个平台挑出适用规则。
     * 通用规则的 platformKey 为 null。
     */
    private List<Map<String, Object>> toRuleList(List<AuditRule> rules, List<AuditPlatform> platforms) {
        Map<Long, String> idToKey = platforms.stream()
                .collect(Collectors.toMap(AuditPlatform::getId, AuditPlatform::getPlatformKey));
        List<Map<String, Object>> list = new ArrayList<>();
        for (AuditRule r : rules) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("code", r.getRuleCode());
            m.put("name", r.getRuleName());
            m.put("category", r.getCategory());
            m.put("content", r.getRuleContent());
            m.put("source", r.getSource());
            m.put("suggestedLevel", r.getSuggestedLevel());
            m.put("platformKey", r.getPlatformId() == null ? null : idToKey.get(r.getPlatformId()));
            list.add(m);
        }
        return list;
    }

    // ------------------------------------------------------------------
    // 落库
    // ------------------------------------------------------------------

    @SuppressWarnings("unchecked")
    private void saveResults(BizArticle article, Map<String, Object> response,
                             Map<String, AuditPlatform> platformByKey) {
        Object resultsObj = response.get("results");
        if (!(resultsObj instanceof List<?> results)) {
            log.warn("适配响应缺少 results，跳过落库：articleId={}", article.getId());
            return;
        }
        for (Object item : results) {
            if (!(item instanceof Map<?, ?> raw)) {
                continue;
            }
            Map<String, Object> r = (Map<String, Object>) raw;
            String key = str(r.get("platformKey"));
            AuditPlatform platform = platformByKey.get(key);
            if (platform == null) {
                continue;
            }

            AuditAdaptation row = new AuditAdaptation();
            row.setArticleId(article.getId());
            row.setPlatformId(platform.getId());
            row.setAdaptedTitle(cut(str(r.get("title")), 300));
            row.setAdaptedContent(str(r.get("content")));
            row.setAdaptedTags(cut(String.join(" ", asStringList(r.get("tags"))), 300));
            row.setFormatCheck(cut(summarizeFormat(r), 1000));
            row.setComplianceCheck(cut(summarizeCompliance(r), 1000));
            row.setVersion(nextVersion(article.getId(), platform.getId()));
            row.setAdaptedBy(StpUtil.getLoginIdAsLong());
            adaptationMapper.insert(row);
        }
    }

    /** 版本号 = 同一稿件 + 同一平台已有记录的最大 version + 1 */
    private int nextVersion(Long articleId, Long platformId) {
        AuditAdaptation last = adaptationMapper.selectOne(
                Wrappers.<AuditAdaptation>lambdaQuery()
                        .eq(AuditAdaptation::getArticleId, articleId)
                        .eq(AuditAdaptation::getPlatformId, platformId)
                        .orderByDesc(AuditAdaptation::getVersion)
                        .last("LIMIT 1"));
        return last == null || last.getVersion() == null ? 1 : last.getVersion() + 1;
    }

    private String summarizeFormat(Map<String, Object> r) {
        Map<String, Object> f = asMap(r.get("formatCheck"));
        boolean passed = Boolean.TRUE.equals(f.get("passed"));
        StringBuilder sb = new StringBuilder(passed ? "通过" : "未通过");
        sb.append("｜标题 ").append(str(f.get("titleLen"))).append(" 字");
        sb.append("，正文 ").append(str(f.get("contentLen"))).append(" 字");
        sb.append("，标签 ").append(str(f.get("tagCount"))).append(" 个");
        List<String> issues = asStringList(f.get("issues"));
        if (!issues.isEmpty()) {
            sb.append("；问题：").append(String.join("；", issues));
        }
        return sb.toString();
    }

    private String summarizeCompliance(Map<String, Object> r) {
        Map<String, Object> c = asMap(r.get("compliance"));
        String level = str(c.get("riskLevelText"));
        if (!StringUtils.hasText(level)) {
            level = "等级 " + str(c.get("riskLevel"));
        }
        StringBuilder sb = new StringBuilder(level);
        String reason = str(c.get("reason"));
        if (StringUtils.hasText(reason)) {
            sb.append("｜").append(reason);
        }
        List<String> codes = new ArrayList<>();
        for (Object h : asList(c.get("hitRules"))) {
            String code = str(asMap(h).get("code"));
            if (StringUtils.hasText(code)) {
                codes.add(code);
            }
        }
        if (!codes.isEmpty()) {
            sb.append("｜命中规则：").append(String.join("、", codes));
        }
        return sb.toString();
    }

    private AdaptationVO toVO(AuditAdaptation row, AuditPlatform platform) {
        AdaptationVO vo = new AdaptationVO();
        vo.setId(row.getId());
        vo.setArticleId(row.getArticleId());
        vo.setPlatformKey(platform == null ? null : platform.getPlatformKey());
        vo.setPlatformName(platform == null ? "未知平台" : platform.getPlatformName());
        vo.setVersion(row.getVersion());
        vo.setTitle(row.getAdaptedTitle());
        vo.setContent(row.getAdaptedContent());
        vo.setTags(StringUtils.hasText(row.getAdaptedTags())
                ? Arrays.asList(row.getAdaptedTags().trim().split("\\s+"))
                : List.of());
        vo.setFormatCheck(row.getFormatCheck());
        vo.setComplianceCheck(row.getComplianceCheck());
        vo.setCreateTime(row.getCreateTime());
        return vo;
    }

    // ------------------------------------------------------------------
    // 权限与工具
    // ------------------------------------------------------------------

    private BizArticle mustGet(Long articleId) {
        BizArticle article = articleMapper.selectById(articleId);
        if (article == null) {
            throw new BizException("稿件不存在");
        }
        return article;
    }

    /** 功能权限由 @SaCheckPermission 控制；这里判断数据权限：非管理/审核角色只能适配自己的稿件 */
    private void assertCanAdapt(BizArticle article) {
        if (isStaff()) {
            return;
        }
        if (!article.getAuthorId().equals(StpUtil.getLoginIdAsLong())) {
            throw new BizException(403, "只能适配自己的稿件");
        }
    }

    private boolean isStaff() {
        return StpUtil.hasPermission("article:list")
                || StpUtil.hasPermission("audit:workbench")
                || StpUtil.hasPermission("audit:record");
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> asMap(Object o) {
        return o instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of();
    }

    private List<?> asList(Object o) {
        return o instanceof List<?> l ? l : List.of();
    }

    private List<String> asStringList(Object o) {
        List<String> list = new ArrayList<>();
        for (Object item : asList(o)) {
            String s = str(item);
            if (StringUtils.hasText(s)) {
                list.add(s);
            }
        }
        return list;
    }

    private String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    /** 按 Unicode 码点截断，避免把 emoji 的代理对切成半个字符（数据库会报错或存成乱码） */
    private String cut(String s, int maxCodePoints) {
        if (s == null || s.codePointCount(0, s.length()) <= maxCodePoints) {
            return s;
        }
        return s.substring(0, s.offsetByCodePoints(0, maxCodePoints));
    }
}

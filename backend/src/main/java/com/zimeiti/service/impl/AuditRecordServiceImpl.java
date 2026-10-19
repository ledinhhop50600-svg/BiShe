package com.zimeiti.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zimeiti.common.AuditTriggerType;
import com.zimeiti.common.BizException;
import com.zimeiti.common.ContentHash;
import com.zimeiti.common.PageResult;
import com.zimeiti.common.ReviewActions;
import com.zimeiti.common.RiskLevels;
import com.zimeiti.entity.AuditRecord;
import com.zimeiti.entity.AuditReview;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.entity.SysUser;
import com.zimeiti.mapper.AuditRecordMapper;
import com.zimeiti.mapper.AuditReviewMapper;
import com.zimeiti.mapper.BizArticleMapper;
import com.zimeiti.mapper.SysUserMapper;
import com.zimeiti.service.AuditRecordService;
import com.zimeiti.vo.AuditRecordVO;
import com.zimeiti.vo.AuditReviewVO;
import com.zimeiti.vo.ViolationVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * 审核记录服务实现。
 * <p>设计要点：
 *  1. **每次判定都留一条**，不覆盖旧记录 —— 重新初审、失败、内容修改后的复审都能追溯；
 *  2. **失败也留痕**（riskLevel=-1，modelName=agent-failed），便于统计可用率；
 *  3. 记录是否"过期"由 `create_time` 与稿件 `update_time` 比较得出 —— 稿件被修改过，
 *     旧结论就不能再用于采纳/改判。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuditRecordServiceImpl implements AuditRecordService {

    private static final String MODEL_AGENT_FAILED = "agent-failed";

    private final AuditRecordMapper recordMapper;
    private final AuditReviewMapper reviewMapper;
    private final BizArticleMapper articleMapper;
    private final SysUserMapper userMapper;
    private final ObjectMapper jsonMapper;

    @Override
    public Long saveAgentResult(Long articleId, String triggerType, Long platformId,
                                String contentHash, Map<String, Object> result,
                                boolean failed, String error) {
        AuditRecord record = new AuditRecord();
        record.setArticleId(articleId);
        record.setTriggerType(AuditTriggerType.of(triggerType).code());
        record.setPlatformId(platformId);
        record.setContentHash(contentHash);

        if (failed) {
            record.setRiskLevel(-1);
            record.setReason("智能体不可用：" + (StringUtils.hasText(error) ? error : "未知错误"));
            record.setHitRuleCodes("");
            record.setViolationFragments("[]");
            record.setSuggestion("请由审核员人工判定。");
            record.setModelName(MODEL_AGENT_FAILED);
            record.setPromptTokens(0);
            record.setCompletionTokens(0);
            record.setDurationMs(0);
        } else {
            record.setRiskLevel(intVal(result.get("riskLevel"), -1));
            record.setReason(str(result.get("reason")));
            record.setHitRuleCodes(cut(joinCodes(result.get("hitRules")), 300));
            record.setViolationFragments(cut(toJson(result.get("violations")), 8000));
            record.setSuggestion(str(result.get("suggestion")));
            record.setModelName(cut(str(result.get("model")), 50));
            Map<String, Object> usage = asMap(result.get("usage"));
            record.setPromptTokens(intVal(usage.get("promptTokens"), 0));
            record.setCompletionTokens(intVal(usage.get("completionTokens"), 0));
            record.setDurationMs(intVal(result.get("durationMs"), 0));
        }
        recordMapper.insert(record);
        return record.getId();
    }

    @Override
    public Map<String, Object> feedback(Long articleId) {
        BizArticle article = articleMapper.selectById(articleId);
        if (article == null) {
            throw new BizException("稿件不存在");
        }
        AuditRecord record = latest(articleId);
        AuditReview review = latestReview(articleId);
        boolean stale = record != null && isStale(record, article);
        // 只展示"针对最新这条记录"的审核意见；如果稿件后来被改过，旧意见也不再生效
        if (review != null && (record == null || stale
                || !review.getAuditRecordId().equals(record.getId()))) {
            review = null;
        }
        String authorName = userName(article.getAuthorId());
        String reviewerName = review == null ? null : userName(review.getReviewerId());

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("articleId", articleId);
        out.put("articleUpdateTime", article.getUpdateTime());
        out.put("record", record == null ? null
                : toVO(record, article, authorName, review, reviewerName));
        out.put("review", review == null ? null : toReviewVO(review, reviewerName));
        return out;
    }

    @Override
    public PageResult<AuditRecordVO> page(long pageNum, long pageSize,
                                          Integer triggerType, Integer riskLevel, Boolean onlyOverride) {
        var query = Wrappers.<AuditRecord>lambdaQuery()
                .eq(triggerType != null, AuditRecord::getTriggerType, triggerType)
                .eq(riskLevel != null, AuditRecord::getRiskLevel, riskLevel)
                .orderByDesc(AuditRecord::getId);

        if (Boolean.TRUE.equals(onlyOverride)) {
            List<Long> recordIds = reviewMapper.selectList(
                            Wrappers.<AuditReview>lambdaQuery().eq(AuditReview::getAction, ReviewActions.OVERRIDE))
                    .stream().map(AuditReview::getAuditRecordId).distinct().toList();
            if (recordIds.isEmpty()) {
                return PageResult.of(List.of(), 0, pageNum, pageSize);
            }
            query.in(AuditRecord::getId, recordIds);
        }

        Page<AuditRecord> page = recordMapper.selectPage(new Page<>(pageNum, pageSize), query);
        List<AuditRecord> records = page.getRecords();
        if (records.isEmpty()) {
            return PageResult.of(List.of(), page.getTotal(), page.getCurrent(), page.getSize());
        }

        // 批量取稿件、审核意见、审核员，避免逐条查询（N+1）
        Set<Long> articleIds = records.stream().map(AuditRecord::getArticleId)
                .collect(Collectors.toCollection(LinkedHashSet::new));
        Map<Long, BizArticle> articleById = articleMapper.selectBatchIds(articleIds).stream()
                .collect(Collectors.toMap(BizArticle::getId, a -> a));

        Set<Long> recordIds = records.stream().map(AuditRecord::getId)
                .collect(Collectors.toCollection(LinkedHashSet::new));
        Map<Long, AuditReview> reviewByRecord = new HashMap<>();
        for (AuditReview r : reviewMapper.selectList(Wrappers.<AuditReview>lambdaQuery()
                .in(AuditReview::getAuditRecordId, recordIds)
                .orderByDesc(AuditReview::getId))) {
            reviewByRecord.putIfAbsent(r.getAuditRecordId(), r);
        }

        Set<Long> userIds = Stream.concat(
                        articleById.values().stream().map(BizArticle::getAuthorId),
                        reviewByRecord.values().stream().map(AuditReview::getReviewerId))
                .filter(java.util.Objects::nonNull)
                .collect(Collectors.toCollection(LinkedHashSet::new));
        Map<Long, String> nameById = userIds.isEmpty() ? Map.of()
                : userMapper.selectBatchIds(userIds).stream()
                .collect(Collectors.toMap(SysUser::getId, SysUser::getNickname, (a, b) -> a));

        List<AuditRecordVO> list = new ArrayList<>();
        for (AuditRecord r : records) {
            BizArticle article = articleById.get(r.getArticleId());
            AuditReview review = reviewByRecord.get(r.getId());
            list.add(toVO(r, article,
                    article == null ? null : nameById.get(article.getAuthorId()),
                    review,
                    review == null ? null : nameById.get(review.getReviewerId())));
        }
        return PageResult.of(list, page.getTotal(), page.getCurrent(), page.getSize());
    }

    @Override
    public Map<String, Object> stats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("recordCount", recordMapper.selectCount(null));
        out.put("risk0", countByRisk(0));
        out.put("risk1", countByRisk(1));
        out.put("risk2", countByRisk(2));
        out.put("risk3", countByRisk(3));
        out.put("failedCount", recordMapper.selectCount(Wrappers.<AuditRecord>lambdaQuery()
                .eq(AuditRecord::getModelName, MODEL_AGENT_FAILED)));

        long adopt = reviewMapper.selectCount(Wrappers.<AuditReview>lambdaQuery()
                .eq(AuditReview::getAction, ReviewActions.ADOPT));
        long override = reviewMapper.selectCount(Wrappers.<AuditReview>lambdaQuery()
                .eq(AuditReview::getAction, ReviewActions.OVERRIDE));
        long manual = reviewMapper.selectCount(Wrappers.<AuditReview>lambdaQuery()
                .eq(AuditReview::getAction, ReviewActions.MANUAL));
        out.put("adoptCount", adopt);
        out.put("overrideCount", override);
        out.put("manualCount", manual);
        // 改判率的分母只算"有可用初判"的审核（采纳 + 改判），人工判定不计入
        double rate = (adopt + override) == 0 ? 0
                : Math.round(override * 1000.0 / (adopt + override)) / 10.0;
        out.put("overrideRate", rate);
        return out;
    }

    @Override
    public AuditRecord latest(Long articleId) {
        return recordMapper.selectOne(Wrappers.<AuditRecord>lambdaQuery()
                .eq(AuditRecord::getArticleId, articleId)
                .orderByDesc(AuditRecord::getId)
                .last("LIMIT 1"));
    }

    private AuditReview latestReview(Long articleId) {
        return reviewMapper.selectOne(Wrappers.<AuditReview>lambdaQuery()
                .eq(AuditReview::getArticleId, articleId)
                .orderByDesc(AuditReview::getId)
                .last("LIMIT 1"));
    }

    private Long countByRisk(int level) {
        return recordMapper.selectCount(Wrappers.<AuditRecord>lambdaQuery()
                .eq(AuditRecord::getRiskLevel, level));
    }

    /**
     * 记录是否已过期。
     * <p>优先用内容哈希（精确到"这一版文字"）；没有哈希的旧记录退回时间比较。
     */
    private boolean isStale(AuditRecord record, BizArticle article) {
        if (record == null || article == null) {
            return false;
        }
        if (StringUtils.hasText(record.getContentHash())) {
            return !record.getContentHash().equals(
                    ContentHash.of(article.getTitle(), article.getContent()));
        }
        return record.getCreateTime() != null && article.getUpdateTime() != null
                && record.getCreateTime().isBefore(article.getUpdateTime());
    }

    // ------------------------------------------------------------------
    // 转换与工具
    // ------------------------------------------------------------------

    private AuditRecordVO toVO(AuditRecord r, BizArticle article, String authorName,
                               AuditReview review, String reviewerName) {
        AuditRecordVO vo = new AuditRecordVO();
        vo.setId(r.getId());
        vo.setArticleId(r.getArticleId());
        vo.setArticleTitle(article == null ? "（稿件已删除）" : article.getTitle());
        vo.setAuthorName(authorName);
        vo.setTriggerType(r.getTriggerType());
        vo.setTriggerText(AuditTriggerType.textOf(r.getTriggerType()));
        vo.setRiskLevel(r.getRiskLevel());
        vo.setRiskLevelText(RiskLevels.text(r.getRiskLevel()));
        vo.setReason(r.getReason());
        vo.setHitRuleCodes(r.getHitRuleCodes());
        vo.setViolations(parseViolations(r.getViolationFragments()));
        vo.setSuggestion(r.getSuggestion());
        vo.setModelName(r.getModelName());
        vo.setPromptTokens(r.getPromptTokens());
        vo.setCompletionTokens(r.getCompletionTokens());
        vo.setDurationMs(r.getDurationMs());
        vo.setCreateTime(r.getCreateTime());
        if (article != null) {
            vo.setArticleUpdateTime(article.getUpdateTime());
            vo.setStale(isStale(r, article));
        } else {
            vo.setStale(false);
        }
        if (review != null) {
            vo.setReviewAction(review.getAction());
            vo.setReviewActionText(ReviewActions.text(review.getAction()));
            vo.setFinalLevel(review.getFinalLevel());
            vo.setFinalLevelText(RiskLevels.text(review.getFinalLevel()));
            vo.setReviewRemark(review.getRemark());
            vo.setReviewerName(reviewerName);
            vo.setReviewTime(review.getCreateTime());
        }
        return vo;
    }

    private AuditReviewVO toReviewVO(AuditReview review, String reviewerName) {
        AuditReviewVO vo = new AuditReviewVO();
        vo.setId(review.getId());
        vo.setAuditRecordId(review.getAuditRecordId());
        vo.setAction(review.getAction());
        vo.setActionText(ReviewActions.text(review.getAction()));
        vo.setFinalLevel(review.getFinalLevel());
        vo.setFinalLevelText(RiskLevels.text(review.getFinalLevel()));
        vo.setRemark(review.getRemark());
        vo.setReviewerName(reviewerName);
        vo.setCreateTime(review.getCreateTime());
        return vo;
    }

    private String userName(Long userId) {
        if (userId == null) {
            return null;
        }
        SysUser user = userMapper.selectById(userId);
        return user == null ? "未知用户" : user.getNickname();
    }

    private List<ViolationVO> parseViolations(String json) {
        if (!StringUtils.hasText(json)) {
            return List.of();
        }
        try {
            List<ViolationVO> list = jsonMapper.readValue(json, new TypeReference<List<ViolationVO>>() {
            });
            return list == null ? List.of() : list;
        } catch (Exception e) {
            log.warn("解析违规片段失败：{}", e.getMessage());
            return List.of();
        }
    }

    private String toJson(Object value) {
        if (value == null) {
            return "[]";
        }
        try {
            return jsonMapper.writeValueAsString(value);
        } catch (Exception e) {
            log.warn("序列化违规片段失败：{}", e.getMessage());
            return "[]";
        }
    }

    private String joinCodes(Object hitRules) {
        if (!(hitRules instanceof List<?> list)) {
            return "";
        }
        List<String> codes = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> m) {
                String code = str(m.get("code"));
                if (StringUtils.hasText(code)) {
                    codes.add(code);
                }
            }
        }
        return String.join(",", codes);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> asMap(Object o) {
        return o instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of();
    }

    private String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    private int intVal(Object o, int defaultValue) {
        if (o instanceof Number n) {
            return n.intValue();
        }
        try {
            return Integer.parseInt(str(o));
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    /** 按码点截断，避免切断 emoji 的代理对 */
    private String cut(String s, int maxCodePoints) {
        if (s == null || s.codePointCount(0, s.length()) <= maxCodePoints) {
            return s;
        }
        return s.substring(0, s.offsetByCodePoints(0, maxCodePoints));
    }
}

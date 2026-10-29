package com.zimeiti.service.impl;

import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.ReviewActions;
import com.zimeiti.common.RiskLevels;
import com.zimeiti.entity.AuditAdaptation;
import com.zimeiti.entity.AuditPlatform;
import com.zimeiti.entity.AuditRecord;
import com.zimeiti.entity.AuditReview;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.entity.BizCategory;
import com.zimeiti.entity.BizReport;
import com.zimeiti.mapper.AuditAdaptationMapper;
import com.zimeiti.mapper.AuditPlatformMapper;
import com.zimeiti.mapper.AuditRecordMapper;
import com.zimeiti.mapper.AuditReviewMapper;
import com.zimeiti.mapper.BizArticleMapper;
import com.zimeiti.mapper.BizCategoryMapper;
import com.zimeiti.mapper.BizReportMapper;
import com.zimeiti.mapper.SysUserMapper;
import com.zimeiti.service.DashboardService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 看板聚合实现。
 * <p>数据量很小（教学项目），所以直接查列表在内存里分组，避免为每种图写一条 SQL；
 * 如果以后数据量上来，应改为数据库聚合（GROUP BY）并加索引。
 * <p>权限口径：管理员看全站，审核员看全站任务，创作者只看自己的稿件/审核/适配。
 */
@Service
@RequiredArgsConstructor
public class DashboardServiceImpl implements DashboardService {

    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("MM-dd");

    private final SysUserMapper userMapper;
    private final BizArticleMapper articleMapper;
    private final BizReportMapper reportMapper;
    private final AuditRecordMapper recordMapper;
    private final AuditReviewMapper reviewMapper;
    private final AuditAdaptationMapper adaptationMapper;
    private final AuditPlatformMapper platformMapper;
    private final BizCategoryMapper categoryMapper;

    @Override
    public Map<String, Object> overview() {
        boolean admin = StpUtil.hasPermission("article:list");
        boolean reviewer = !admin && StpUtil.hasPermission("audit:workbench");
        String scope = admin ? "admin" : (reviewer ? "reviewer" : "creator");
        long me = StpUtil.getLoginIdAsLong();

        List<BizArticle> articles = loadArticles(scope, me);
        Set<Long> articleIds = articles.stream().map(BizArticle::getId).collect(Collectors.toSet());
        List<AuditRecord> records = loadRecords(scope, articleIds);
        List<AuditReview> reviews = loadReviews(scope, articleIds);
        List<AuditAdaptation> adaptations = loadAdaptations(scope, articleIds);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("scope", scope);
        out.put("scopeLabel", admin ? "平台全局" : reviewer ? "审核任务" : "我的创作");
        out.put("date", LocalDate.now().toString());
        out.put("cards", buildCards(scope, me, articles, reviews));
        out.put("statusDistribution", statusDistribution(articles));
        out.put("riskDistribution", riskDistribution(records));
        out.put("reviewDistribution", reviewDistribution(reviews));
        out.put("trend", trend(articles));
        out.put("categoryDistribution", categoryDistribution(articles));
        out.put("platformAdaptation", platformAdaptation(adaptations));
        out.put("recentAudits", recentAudits(records));
        out.put("recentArticles", recentArticles(articles));

        long adopt = reviews.stream().filter(r -> Objects.equals(r.getAction(), ReviewActions.ADOPT)).count();
        long override = reviews.stream().filter(r -> Objects.equals(r.getAction(), ReviewActions.OVERRIDE)).count();
        long manual = reviews.stream().filter(r -> Objects.equals(r.getAction(), ReviewActions.MANUAL)).count();
        Map<String, Object> pulse = new LinkedHashMap<>();
        pulse.put("agentRecordCount", records.size());
        pulse.put("adaptationCount", adaptations.size());
        pulse.put("adoptCount", adopt);
        pulse.put("overrideCount", override);
        pulse.put("manualCount", manual);
        pulse.put("overrideRate", (adopt + override) == 0 ? 0.0
                : Math.round(override * 1000.0 / (adopt + override)) / 10.0);
        out.put("pulse", pulse);
        return out;
    }

    // ------------------------------------------------------------------
    // 取数
    // ------------------------------------------------------------------

    private List<BizArticle> loadArticles(String scope, long me) {
        var q = Wrappers.<BizArticle>lambdaQuery().orderByDesc(BizArticle::getUpdateTime);
        if ("creator".equals(scope)) {
            q.eq(BizArticle::getAuthorId, me);
        }
        return articleMapper.selectList(q);
    }

    private List<AuditRecord> loadRecords(String scope, Set<Long> articleIds) {
        if ("creator".equals(scope) && articleIds.isEmpty()) {
            return List.of();
        }
        var q = Wrappers.<AuditRecord>lambdaQuery().orderByDesc(AuditRecord::getId);
        if ("creator".equals(scope)) {
            q.in(AuditRecord::getArticleId, articleIds);
        }
        return recordMapper.selectList(q);
    }

    private List<AuditReview> loadReviews(String scope, Set<Long> articleIds) {
        if ("creator".equals(scope) && articleIds.isEmpty()) {
            return List.of();
        }
        var q = Wrappers.<AuditReview>lambdaQuery().orderByDesc(AuditReview::getId);
        if ("creator".equals(scope)) {
            q.in(AuditReview::getArticleId, articleIds);
        }
        return reviewMapper.selectList(q);
    }

    private List<AuditAdaptation> loadAdaptations(String scope, Set<Long> articleIds) {
        if ("creator".equals(scope) && articleIds.isEmpty()) {
            return List.of();
        }
        var q = Wrappers.<AuditAdaptation>lambdaQuery().orderByDesc(AuditAdaptation::getId);
        if ("creator".equals(scope)) {
            q.in(AuditAdaptation::getArticleId, articleIds);
        }
        return adaptationMapper.selectList(q);
    }

    // ------------------------------------------------------------------
    // 卡片
    // ------------------------------------------------------------------

    private List<Map<String, Object>> buildCards(String scope, long me,
                                                  List<BizArticle> articles,
                                                  List<AuditReview> reviews) {
        List<Map<String, Object>> cards = new ArrayList<>();
        if ("admin".equals(scope)) {
            cards.add(card("userCount", "用户总数", userMapper.selectCount(null), "人", "teal"));
            cards.add(card("articleCount", "稿件总数", articles.size(), "篇", "gold"));
            cards.add(card("pendingCount", "待审核", countStatus(articles, 1), "篇", "terracotta"));
            cards.add(card("publishedCount", "已发布", countStatus(articles, 2), "篇", "sage"));
        } else if ("reviewer".equals(scope)) {
            cards.add(card("pendingCount", "待审核", countStatus(articles, 1), "篇", "teal"));
            cards.add(card("pendingReportCount", "待处理举报",
                    reportMapper.selectCount(Wrappers.<BizReport>lambdaQuery().eq(BizReport::getStatus, 0)),
                    "条", "terracotta"));
            cards.add(card("todaySubmittedCount", "今日新增", articles.stream()
                    .filter(a -> a.getCreateTime() != null
                            && a.getCreateTime().toLocalDate().equals(LocalDate.now()))
                    .count(), "篇", "gold"));
            cards.add(card("todayProcessedCount", "今日已处理", reviews.stream()
                    .filter(r -> Objects.equals(r.getReviewerId(), me)
                            && r.getCreateTime() != null
                            && r.getCreateTime().toLocalDate().equals(LocalDate.now()))
                    .count(), "条", "sage"));
        } else {
            cards.add(card("myArticleCount", "我的稿件", articles.size(), "篇", "teal"));
            cards.add(card("myPendingCount", "待审核", countStatus(articles, 1), "篇", "gold"));
            cards.add(card("myPublishedCount", "已发布", countStatus(articles, 2), "篇", "sage"));
            cards.add(card("myRejectedCount", "被驳回", countStatus(articles, 3), "篇", "terracotta"));
        }
        return cards;
    }

    private Map<String, Object> card(String key, String label, long value, String unit, String tone) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("key", key);
        m.put("label", label);
        m.put("value", value);
        m.put("unit", unit);
        m.put("tone", tone);
        return m;
    }

    private long countStatus(List<BizArticle> articles, int status) {
        return articles.stream().filter(a -> Objects.equals(a.getStatus(), status)).count();
    }

    // ------------------------------------------------------------------
    // 分布与趋势
    // ------------------------------------------------------------------

    private List<Map<String, Object>> statusDistribution(List<BizArticle> articles) {
        String[] names = {"草稿", "待审核", "已发布", "已驳回", "已阻断", "已下架"};
        List<Map<String, Object>> list = new ArrayList<>();
        for (int i = 0; i < names.length; i++) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("name", names[i]);
            m.put("status", i);
            m.put("value", countStatus(articles, i));
            list.add(m);
        }
        return list;
    }

    private List<Map<String, Object>> riskDistribution(List<AuditRecord> records) {
        int[] levels = {-1, 0, 1, 2, 3};
        List<Map<String, Object>> list = new ArrayList<>();
        for (int level : levels) {
            long count = records.stream().filter(r -> Objects.equals(r.getRiskLevel(), level)).count();
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("name", RiskLevels.text(level));
            m.put("level", level);
            m.put("value", count);
            list.add(m);
        }
        return list;
    }

    private List<Map<String, Object>> reviewDistribution(List<AuditReview> reviews) {
        int[] actions = {ReviewActions.ADOPT, ReviewActions.OVERRIDE, ReviewActions.MANUAL};
        List<Map<String, Object>> list = new ArrayList<>();
        for (int action : actions) {
            long count = reviews.stream().filter(r -> Objects.equals(r.getAction(), action)).count();
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("name", ReviewActions.text(action));
            m.put("action", action);
            m.put("value", count);
            list.add(m);
        }
        return list;
    }

    private List<Map<String, Object>> trend(List<BizArticle> articles) {
        LocalDate today = LocalDate.now();
        Map<LocalDate, long[]> days = new LinkedHashMap<>();
        // 用 14 天窗口：教学演示数据可能不是当天产生的，7 天会全是 0，看不出趋势
        for (int i = 13; i >= 0; i--) {
            days.put(today.minusDays(i), new long[2]);
        }
        for (BizArticle article : articles) {
            LocalDate created = toDate(article.getCreateTime());
            if (created != null && days.containsKey(created)) {
                days.get(created)[0]++;
            }
            LocalDate published = toDate(article.getPublishTime());
            if (published != null && days.containsKey(published)) {
                days.get(published)[1]++;
            }
        }
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map.Entry<LocalDate, long[]> e : days.entrySet()) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("date", e.getKey().format(DAY));
            m.put("submitted", e.getValue()[0]);
            m.put("published", e.getValue()[1]);
            list.add(m);
        }
        return list;
    }

    private List<Map<String, Object>> categoryDistribution(List<BizArticle> articles) {
        Map<Long, Long> counts = new HashMap<>();
        long uncategorized = 0;
        for (BizArticle a : articles) {
            if (a.getCategoryId() == null) {
                uncategorized++;
            } else {
                counts.merge(a.getCategoryId(), 1L, Long::sum);
            }
        }
        Map<Long, String> names = categoryMapper.selectList(null).stream()
                .collect(Collectors.toMap(BizCategory::getId, BizCategory::getName));
        List<Map<String, Object>> list = counts.entrySet().stream()
                .sorted(Map.Entry.<Long, Long>comparingByValue().reversed())
                .limit(6)
                .map(e -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("name", names.getOrDefault(e.getKey(), "未分类"));
                    m.put("value", e.getValue());
                    return m;
                })
                .collect(Collectors.toList());
        if (uncategorized > 0) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("name", "未分类");
            m.put("value", uncategorized);
            list.add(m);
        }
        return list;
    }

    private List<Map<String, Object>> platformAdaptation(List<AuditAdaptation> adaptations) {
        Map<Long, Long> counts = new HashMap<>();
        for (AuditAdaptation a : adaptations) {
            if (a.getPlatformId() != null) {
                counts.merge(a.getPlatformId(), 1L, Long::sum);
            }
        }
        Map<Long, String> names = platformMapper.selectList(null).stream()
                .collect(Collectors.toMap(AuditPlatform::getId, AuditPlatform::getPlatformName));
        return counts.entrySet().stream()
                .sorted(Map.Entry.<Long, Long>comparingByValue().reversed())
                .map(e -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("name", names.getOrDefault(e.getKey(), "未知平台"));
                    m.put("value", e.getValue());
                    return m;
                })
                .collect(Collectors.toList());
    }

    // ------------------------------------------------------------------
    // 最近动态
    // ------------------------------------------------------------------

    private List<Map<String, Object>> recentAudits(List<AuditRecord> records) {
        List<AuditRecord> top = records.stream()
                .sorted(Comparator.comparing(AuditRecord::getId).reversed())
                .limit(5)
                .toList();
        if (top.isEmpty()) {
            return List.of();
        }
        Set<Long> articleIds = top.stream().map(AuditRecord::getArticleId).collect(Collectors.toSet());
        Map<Long, BizArticle> articleMap = articleMapper.selectBatchIds(articleIds).stream()
                .collect(Collectors.toMap(BizArticle::getId, a -> a));
        Set<Long> recordIds = top.stream().map(AuditRecord::getId).collect(Collectors.toSet());
        Map<Long, AuditReview> reviewMap = new HashMap<>();
        for (AuditReview r : reviewMapper.selectList(Wrappers.<AuditReview>lambdaQuery()
                .in(AuditReview::getAuditRecordId, recordIds)
                .orderByDesc(AuditReview::getId))) {
            reviewMap.putIfAbsent(r.getAuditRecordId(), r);
        }
        List<Map<String, Object>> list = new ArrayList<>();
        for (AuditRecord r : top) {
            BizArticle a = articleMap.get(r.getArticleId());
            AuditReview review = reviewMap.get(r.getId());
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", r.getId());
            m.put("articleTitle", a == null ? "（稿件已删除）" : a.getTitle());
            m.put("riskLevel", r.getRiskLevel());
            m.put("riskLevelText", RiskLevels.text(r.getRiskLevel()));
            m.put("modelName", r.getModelName());
            m.put("createTime", r.getCreateTime());
            m.put("reviewActionText", review == null ? null : ReviewActions.text(review.getAction()));
            list.add(m);
        }
        return list;
    }

    private List<Map<String, Object>> recentArticles(List<BizArticle> articles) {
        return articles.stream()
                .sorted(Comparator.comparing(BizArticle::getUpdateTime,
                        Comparator.nullsLast(Comparator.reverseOrder())))
                .limit(6)
                .map(a -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", a.getId());
                    m.put("title", a.getTitle());
                    m.put("status", a.getStatus());
                    m.put("statusText", statusText(a.getStatus()));
                    m.put("riskLevel", a.getRiskLevel());
                    m.put("riskLevelText", RiskLevels.text(a.getRiskLevel()));
                    m.put("updateTime", a.getUpdateTime());
                    return m;
                })
                .collect(Collectors.toList());
    }

    private String statusText(Integer status) {
        if (status == null) {
            return "未知";
        }
        return switch (status) {
            case 0 -> "草稿";
            case 1 -> "待审核";
            case 2 -> "已发布";
            case 3 -> "已驳回";
            case 4 -> "已阻断";
            case 5 -> "已下架";
            default -> "未知";
        };
    }

    private LocalDate toDate(LocalDateTime time) {
        return time == null ? null : time.toLocalDate();
    }
}

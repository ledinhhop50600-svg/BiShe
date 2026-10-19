package com.zimeiti.service.impl;

import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zimeiti.common.AuditTriggerType;
import com.zimeiti.common.BizException;
import com.zimeiti.common.ContentHash;
import com.zimeiti.common.PageResult;
import com.zimeiti.common.ReviewActions;
import com.zimeiti.dto.ArticleReviewDTO;
import com.zimeiti.dto.ArticleSaveDTO;
import com.zimeiti.entity.AuditRecord;
import com.zimeiti.entity.AuditReview;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.entity.BizArticleTag;
import com.zimeiti.entity.BizCategory;
import com.zimeiti.entity.BizTag;
import com.zimeiti.mapper.AuditRecordMapper;
import com.zimeiti.mapper.AuditReviewMapper;
import com.zimeiti.mapper.BizArticleMapper;
import com.zimeiti.mapper.BizArticleTagMapper;
import com.zimeiti.mapper.BizCategoryMapper;
import com.zimeiti.mapper.BizTagMapper;
import com.zimeiti.mapper.SysUserMapper;
import com.zimeiti.service.ArticleService;
import com.zimeiti.vo.ArticleVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * 稿件服务实现。
 * <p>权限设计：接口层用 @SaCheckPermission 控制"能不能调这个接口"，
 * 服务层再判断"能不能动这篇稿件"（创作者只能操作自己的稿件）——
 * 前者是功能权限，后者是数据权限，两件事不能混。
 */
@Service
@RequiredArgsConstructor
public class ArticleServiceImpl implements ArticleService {

    /** 稿件状态常量：数字在数据库里存，代码里用常量表达意图，避免满屏魔法数字 */
    private static final int STATUS_DRAFT = 0;
    private static final int STATUS_PENDING = 1;
    private static final int STATUS_PUBLISHED = 2;
    private static final int STATUS_REJECTED = 3;
    private static final int STATUS_BLOCKED = 4;
    private static final int STATUS_OFFLINE = 5;

    private final BizArticleMapper articleMapper;
    private final BizArticleTagMapper articleTagMapper;
    private final BizCategoryMapper categoryMapper;
    private final BizTagMapper tagMapper;
    private final SysUserMapper userMapper;
    private final AuditRecordMapper auditRecordMapper;
    private final AuditReviewMapper auditReviewMapper;

    @Override
    public PageResult<ArticleVO> page(long current, long size, String title, Integer status, Long categoryId) {
        Page<BizArticle> page = articleMapper.selectPage(new Page<>(current, size),
                Wrappers.<BizArticle>lambdaQuery()
                        .like(StringUtils.hasText(title), BizArticle::getTitle, title)
                        .eq(status != null, BizArticle::getStatus, status)
                        .eq(categoryId != null, BizArticle::getCategoryId, categoryId)
                        .orderByDesc(BizArticle::getCreateTime));
        return PageResult.of(toVOList(page.getRecords()), page.getTotal(), page.getCurrent(), page.getSize());
    }

    @Override
    public PageResult<ArticleVO> myPage(long current, long size, Integer status) {
        Page<BizArticle> page = articleMapper.selectPage(new Page<>(current, size),
                Wrappers.<BizArticle>lambdaQuery()
                        .eq(BizArticle::getAuthorId, StpUtil.getLoginIdAsLong())
                        .eq(status != null, BizArticle::getStatus, status)
                        .orderByDesc(BizArticle::getCreateTime));
        return PageResult.of(toVOList(page.getRecords()), page.getTotal(), page.getCurrent(), page.getSize());
    }

    @Override
    public PageResult<ArticleVO> plaza(long current, long size, String title, Long categoryId, Long tagId) {
        // 内容广场：所有已发布的稿件（含自己的）
        var wrapper = Wrappers.<BizArticle>lambdaQuery()
                .eq(BizArticle::getStatus, STATUS_PUBLISHED)
                .like(StringUtils.hasText(title), BizArticle::getTitle, title)
                .eq(categoryId != null, BizArticle::getCategoryId, categoryId);

        // 标签筛选：稿件与标签是多对多，先用标签反查稿件 id，再按 id 过滤。
        // 数据量小的时候这样写最直观；稿件量很大时应改为 EXISTS 子查询或加冗余字段。
        if (tagId != null) {
            List<Long> ids = articleTagMapper.selectList(
                            Wrappers.<BizArticleTag>lambdaQuery().eq(BizArticleTag::getTagId, tagId))
                    .stream().map(BizArticleTag::getArticleId).toList();
            if (ids.isEmpty()) {
                return PageResult.of(List.of(), 0, current, size);
            }
            wrapper.in(BizArticle::getId, ids);
        }

        Page<BizArticle> page = articleMapper.selectPage(new Page<>(current, size),
                wrapper.orderByDesc(BizArticle::getPublishTime));
        return PageResult.of(toVOList(page.getRecords()), page.getTotal(), page.getCurrent(), page.getSize());
    }

    @Override
    public ArticleVO detail(Long id) {
        BizArticle article = mustGet(id);
        assertCanView(article);
        return toVO(article);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long save(ArticleSaveDTO dto) {
        BizArticle article = new BizArticle();
        article.setTitle(dto.getTitle());
        article.setContent(dto.getContent());
        article.setSummary(dto.getSummary());
        article.setCoverImage(dto.getCoverImage());
        article.setCategoryId(dto.getCategoryId());
        article.setAuthorId(StpUtil.getLoginIdAsLong());
        article.setStatus(STATUS_DRAFT);   // 新建一律是草稿，不能直接发布
        article.setRiskLevel(-1);
        article.setViewCount(0);
        articleMapper.insert(article);
        saveTags(article.getId(), dto.getTagIds());
        return article.getId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(ArticleSaveDTO dto) {
        if (dto.getId() == null) {
            throw new BizException("缺少稿件 id");
        }
        BizArticle article = mustGet(dto.getId());
        assertIsAuthor(article);
        // 只有草稿和已驳回的稿件可以编辑：已提交审核或已发布的内容不能偷偷改
        if (article.getStatus() != STATUS_DRAFT && article.getStatus() != STATUS_REJECTED) {
            throw new BizException("当前状态不允许编辑（只有草稿和已驳回的稿件可以修改）");
        }
        BizArticle update = new BizArticle();
        update.setId(dto.getId());
        update.setTitle(dto.getTitle());
        update.setContent(dto.getContent());
        update.setSummary(dto.getSummary());
        update.setCoverImage(dto.getCoverImage());
        update.setCategoryId(dto.getCategoryId());
        articleMapper.updateById(update);

        // 标签整体覆盖
        articleTagMapper.delete(Wrappers.<BizArticleTag>lambdaQuery().eq(BizArticleTag::getArticleId, dto.getId()));
        saveTags(dto.getId(), dto.getTagIds());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        BizArticle article = mustGet(id);
        boolean admin = StpUtil.hasPermission("article:delete");
        if (!admin) {
            assertIsAuthor(article);
            if (article.getStatus() != STATUS_DRAFT) {
                throw new BizException("只能删除草稿状态的稿件");
            }
        }
        articleMapper.deleteById(id);
        articleTagMapper.delete(Wrappers.<BizArticleTag>lambdaQuery().eq(BizArticleTag::getArticleId, id));
    }

    @Override
    public void submit(Long id) {
        BizArticle article = mustGet(id);
        assertIsAuthor(article);
        if (article.getStatus() != STATUS_DRAFT && article.getStatus() != STATUS_REJECTED) {
            throw new BizException("只有草稿或已驳回的稿件可以提交审核");
        }
        BizArticle update = new BizArticle();
        update.setId(id);
        update.setStatus(STATUS_PENDING);
        // 重新提交时清掉上一次的驳回原因，避免旧反馈误导创作者
        update.setRejectReason("");
        articleMapper.updateById(update);
    }

    @Override
    public void withdraw(Long id) {
        BizArticle article = mustGet(id);
        assertIsAuthor(article);
        if (article.getStatus() != STATUS_PENDING) {
            throw new BizException("只有待审核的稿件可以撤回");
        }
        BizArticle update = new BizArticle();
        update.setId(id);
        update.setStatus(STATUS_DRAFT);
        articleMapper.updateById(update);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void review(Long id, ArticleReviewDTO dto) {
        BizArticle article = mustGet(id);
        if (article.getStatus() != STATUS_PENDING) {
            throw new BizException("只有待审核的稿件可以审核");
        }
        // 利益冲突隔离：审核员同时也可以是创作者（D2 决策），
        // 但绝不能审核自己的稿件 —— 否则他可以自己放行自己的违规内容。
        if (article.getAuthorId() == StpUtil.getLoginIdAsLong()) {
            throw new BizException("不能审核自己投稿的稿件，请由其他审核员处理");
        }

        String action = dto.getAction();
        int finalLevel = switch (action) {
            case "approve" -> 0;
            case "reject" -> 2;
            case "block" -> 3;
            default -> throw new BizException("不支持的审核动作：" + action);
        };
        if (finalLevel != 0) {
            requireReason(dto);
        }

        // ---- 1) 找到可用的智能体初判；没有 / 失败 / 已过期都视为"人工判定" ----
        String currentHash = ContentHash.of(article.getTitle(), article.getContent());
        AuditRecord record = latestRecord(id);
        boolean fresh = isFresh(record, article, currentHash);
        boolean usable = fresh
                && record.getRiskLevel() != null && record.getRiskLevel() >= 0
                && !"agent-failed".equals(record.getModelName())
                && !"no-agent".equals(record.getModelName())
                && !"content-changed".equals(record.getModelName());
        if (!usable) {
            record = insertManualRecord(id, record == null
                    ? "未运行智能体初审，由审核员直接人工判定。"
                    : "稿件在初审后被修改，原结论已失效，由审核员人工判定。",
                    record == null ? "no-agent" : "content-changed", currentHash);
        }

        // ---- 2) 判断采纳还是改判（口径与页面提示保持一致）----
        int reviewAction;
        if (!usable) {
            reviewAction = ReviewActions.MANUAL;
        } else if (isOverride(record.getRiskLevel(), action)) {
            reviewAction = ReviewActions.OVERRIDE;
            if (!StringUtils.hasText(dto.getReason())) {
                throw new BizException("改判必须填写原因：请说明为什么不采纳智能体的判定");
            }
        } else {
            reviewAction = ReviewActions.ADOPT;
        }

        AuditReview review = new AuditReview();
        review.setAuditRecordId(record.getId());
        review.setArticleId(id);
        review.setReviewerId(StpUtil.getLoginIdAsLong());
        review.setAction(reviewAction);
        review.setFinalLevel(finalLevel);
        review.setRemark(dto.getReason());
        auditReviewMapper.insert(review);

        // ---- 3) 更新稿件状态 ----
        BizArticle update = new BizArticle();
        update.setId(id);
        switch (action) {
            case "approve" -> {
                update.setStatus(STATUS_PUBLISHED);
                update.setPublishTime(LocalDateTime.now());
                update.setRiskLevel(0);
                update.setRejectReason("");
            }
            case "reject" -> {
                update.setStatus(STATUS_REJECTED);
                update.setRiskLevel(2);
                update.setRejectReason(dto.getReason());
            }
            case "block" -> {
                update.setStatus(STATUS_BLOCKED);
                update.setRiskLevel(3);
                update.setRejectReason(dto.getReason());
            }
            default -> throw new BizException("不支持的审核动作：" + action);
        }
        articleMapper.updateById(update);
    }

    /**
     * 改判口径：只有"AI 说通过/疑似、人却驳回或阻断"和"AI 说违规/严重、人却通过"才算改判。
     * <p>「疑似」本来就是交给人工决定的，人工通过或驳回都不算改判 ——
     * 否则改判率会被正常的"疑似转人工"流程虚高，失去分析意义。
     */
    private boolean isOverride(int agentLevel, String action) {
        if ("approve".equals(action)) {
            return agentLevel >= 2;
        }
        return agentLevel == 0;
    }

    private AuditRecord latestRecord(Long articleId) {
        return auditRecordMapper.selectOne(Wrappers.<AuditRecord>lambdaQuery()
                .eq(AuditRecord::getArticleId, articleId)
                .orderByDesc(AuditRecord::getId)
                .last("LIMIT 1"));
    }

    /** 记录是否对应当前这一版内容（优先内容哈希，旧记录退回时间比较） */
    private boolean isFresh(AuditRecord record, BizArticle article, String currentHash) {
        if (record == null) {
            return false;
        }
        if (StringUtils.hasText(record.getContentHash())) {
            return record.getContentHash().equals(currentHash);
        }
        return record.getCreateTime() != null && article.getUpdateTime() != null
                && !record.getCreateTime().isBefore(article.getUpdateTime());
    }

    /** 没有可用的初判时补一条记录：audit_review 必须能追溯到一条判定依据 */
    private AuditRecord insertManualRecord(Long articleId, String reason, String modelName,
                                           String contentHash) {
        AuditRecord record = new AuditRecord();
        record.setArticleId(articleId);
        record.setTriggerType(AuditTriggerType.POST_AUDIT.code());
        record.setRiskLevel(-1);
        record.setReason(reason);
        record.setHitRuleCodes("");
        record.setViolationFragments("[]");
        // 人工记录也绑定当前内容：这样审核完成后稿件更新时间变化不会把它误判为"过期"
        record.setContentHash(contentHash);
        record.setSuggestion("");
        record.setModelName(modelName);
        record.setPromptTokens(0);
        record.setCompletionTokens(0);
        record.setDurationMs(0);
        auditRecordMapper.insert(record);
        return record;
    }

    @Override
    public void offline(Long id) {
        BizArticle article = mustGet(id);
        if (article.getStatus() != STATUS_PUBLISHED) {
            throw new BizException("只有已发布的稿件可以下架");
        }
        BizArticle update = new BizArticle();
        update.setId(id);
        update.setStatus(STATUS_OFFLINE);
        articleMapper.updateById(update);
    }

    // ------------------------------------------------------------------
    // 以下为内部辅助方法
    // ------------------------------------------------------------------

    private BizArticle mustGet(Long id) {
        BizArticle article = articleMapper.selectById(id);
        if (article == null) {
            throw new BizException("稿件不存在");
        }
        return article;
    }

    /** 是否具备"查看所有稿件"的身份（管理员或审核相关角色） */
    private boolean isStaff() {
        return StpUtil.hasPermission("article:list")
                || StpUtil.hasPermission("audit:workbench")
                || StpUtil.hasPermission("audit:record");
    }

    /** 数据权限：创作者只能看自己的稿件 */
    private void assertCanView(BizArticle article) {
        if (isStaff()) {
            return;
        }
        if (!article.getAuthorId().equals(StpUtil.getLoginIdAsLong())) {
            throw new BizException(403, "无权查看他人的稿件");
        }
    }

    /** 数据权限：只有作者本人可以操作 */
    private void assertIsAuthor(BizArticle article) {
        if (!article.getAuthorId().equals(StpUtil.getLoginIdAsLong())) {
            throw new BizException(403, "只能操作自己的稿件");
        }
    }

    private void requireReason(ArticleReviewDTO dto) {
        if (!StringUtils.hasText(dto.getReason())) {
            throw new BizException("驳回或阻断时必须填写原因，创作者需要知道怎么改");
        }
    }

    private void saveTags(Long articleId, List<Long> tagIds) {
        if (tagIds == null || tagIds.isEmpty()) {
            return;
        }
        for (Long tagId : new LinkedHashSet<>(tagIds)) {
            articleTagMapper.insert(new BizArticleTag(articleId, tagId));
        }
    }

    private List<ArticleVO> toVOList(List<BizArticle> articles) {
        List<ArticleVO> list = new ArrayList<>();
        for (BizArticle article : articles) {
            list.add(toVO(article));
        }
        return list;
    }

    private ArticleVO toVO(BizArticle article) {
        ArticleVO vo = new ArticleVO();
        vo.setId(article.getId());
        vo.setTitle(article.getTitle());
        vo.setContent(article.getContent());
        vo.setSummary(article.getSummary());
        vo.setCoverImage(article.getCoverImage());
        vo.setCategoryId(article.getCategoryId());
        vo.setAuthorId(article.getAuthorId());
        vo.setStatus(article.getStatus());
        vo.setRiskLevel(article.getRiskLevel());
        vo.setRejectReason(article.getRejectReason());
        vo.setPublishTime(article.getPublishTime());
        vo.setViewCount(article.getViewCount());
        vo.setCreateTime(article.getCreateTime());
        vo.setUpdateTime(article.getUpdateTime());

        if (article.getCategoryId() != null) {
            BizCategory category = categoryMapper.selectById(article.getCategoryId());
            vo.setCategoryName(category == null ? null : category.getName());
        }
        // 作者昵称：用于列表显示
        var author = userMapper.selectById(article.getAuthorId());
        vo.setAuthorName(author == null ? null : author.getNickname());

        // 标签：先查关联表拿 id，再查名称
        List<Long> tagIds = articleTagMapper.selectList(Wrappers.<BizArticleTag>lambdaQuery()
                        .eq(BizArticleTag::getArticleId, article.getId()))
                .stream().map(BizArticleTag::getTagId).toList();
        vo.setTagIds(tagIds);
        if (!tagIds.isEmpty()) {
            vo.setTagNames(tagMapper.selectByIds(tagIds).stream().map(BizTag::getName).toList());
        } else {
            vo.setTagNames(List.of());
        }
        return vo;
    }
}

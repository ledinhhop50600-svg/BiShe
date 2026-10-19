package com.zimeiti.service.impl;

import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zimeiti.common.BizException;
import com.zimeiti.common.PageResult;
import com.zimeiti.dto.ArticleReviewDTO;
import com.zimeiti.dto.ArticleSaveDTO;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.entity.BizArticleTag;
import com.zimeiti.entity.BizCategory;
import com.zimeiti.entity.BizTag;
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
    public PageResult<ArticleVO> plaza(long current, long size, String title) {
        // 只给"已发布"的稿件，且排除自己的 —— 举报自己的稿件没有意义
        Page<BizArticle> page = articleMapper.selectPage(new Page<>(current, size),
                Wrappers.<BizArticle>lambdaQuery()
                        .eq(BizArticle::getStatus, STATUS_PUBLISHED)
                        .ne(BizArticle::getAuthorId, StpUtil.getLoginIdAsLong())
                        .like(StringUtils.hasText(title), BizArticle::getTitle, title)
                        .orderByDesc(BizArticle::getPublishTime));
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
                requireReason(dto);
                update.setStatus(STATUS_REJECTED);
                update.setRiskLevel(2);
                update.setRejectReason(dto.getReason());
            }
            case "block" -> {
                requireReason(dto);
                update.setStatus(STATUS_BLOCKED);
                update.setRiskLevel(3);
                update.setRejectReason(dto.getReason());
            }
            default -> throw new BizException("不支持的审核动作：" + action);
        }
        articleMapper.updateById(update);
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

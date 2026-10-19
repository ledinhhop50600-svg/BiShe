package com.zimeiti.service;

import com.zimeiti.common.PageResult;
import com.zimeiti.dto.ArticleReviewDTO;
import com.zimeiti.dto.ArticleSaveDTO;
import com.zimeiti.vo.ArticleVO;

/**
 * 稿件服务：内容管理的核心，负责稿件的增删改查与状态流转。
 * <p>稿件状态机（只允许按箭头方向流转，任何"跳跃"都会被拒绝）：
 * <pre>
 *   草稿 ──提交──> 待审核 ──通过──> 已发布 ──下架──> 已下架
 *    ↑              │ ├──驳回──> 已驳回 ──修改后重新提交──> 待审核
 *    └──撤回────────┘ └──阻断──> 已阻断
 * </pre>
 * 状态只能通过这些动作接口改变，**前端不能直接设置 status** —— 否则可以绕过审核直接发布。
 */
public interface ArticleService {

    /** 后台稿件列表（管理员/审核员），可按标题、状态、分类筛选 */
    PageResult<ArticleVO> page(long current, long size, String title, Integer status, Long categoryId);

    /** 我的稿件（创作者视角，只返回自己的） */
    PageResult<ArticleVO> myPage(long current, long size, Integer status);

    /**
     * 内容广场：已发布稿件（含自己的），支持按标题、分类、标签筛选。
     * <p>为什么包含自己的内容：广场的定位是"浏览平台已发布的内容"，
     * 把自己发的内容排除在外并不合理（创作者也会想看看自己发布后的样子）。
     * 需要限制的是"不能举报自己的内容"，这由举报接口把关，而不是靠隐藏内容来实现。
     */
    PageResult<ArticleVO> plaza(long current, long size, String title, Long categoryId, Long tagId);

    /** 稿件详情（创作者只能看自己的） */
    ArticleVO detail(Long id);

    /** 新建稿件（保存为草稿），返回新稿件 id */
    Long save(ArticleSaveDTO dto);

    /** 修改稿件（仅限自己的草稿或已驳回稿件） */
    void update(ArticleSaveDTO dto);

    /** 删除稿件（仅限自己的草稿；管理员可删任意状态） */
    void delete(Long id);

    /** 提交发布申请：草稿/已驳回 -> 待审核 */
    void submit(Long id);

    /** 撤回申请：待审核 -> 草稿 */
    void withdraw(Long id);

    /** 审核：通过 / 驳回 / 阻断 */
    void review(Long id, ArticleReviewDTO dto);

    /** 下架已发布稿件 */
    void offline(Long id);
}

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

    /** 内容广场：已发布稿件（不含自己的），创作者可在这里浏览他人内容并举报 */
    PageResult<ArticleVO> plaza(long current, long size, String title);

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

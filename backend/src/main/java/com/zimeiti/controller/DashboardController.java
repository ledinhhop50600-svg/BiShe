package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.Result;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.entity.BizReport;
import com.zimeiti.mapper.BizArticleMapper;
import com.zimeiti.mapper.BizReportMapper;
import com.zimeiti.mapper.SysUserMapper;
import com.zimeiti.service.AuditRecordService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 数据看板接口。
 * <p>同一份数据对不同角色意义完全不同，所以按角色返回不同的指标集合，并附带 scope 字段
 * 让前端知道该渲染哪一套卡片：
 * <ul>
 *   <li><b>admin</b>：平台全局视角（用户数、稿件数、各状态分布）</li>
 *   <li><b>reviewer</b>：任务视角（待审队列多长、待处理举报多少、今天进来多少稿）</li>
 *   <li><b>creator</b>：个人视角（我的稿件数、我的待审/已发布/被驳回数）</li>
 * </ul>
 * 早前的实现对所有角色都返回全站数据 —— 创作者看到"用户总数 4"毫无意义，
 * 而且把平台级数据暴露给了他，属于设计缺陷。
 */
@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final SysUserMapper userMapper;
    private final BizArticleMapper articleMapper;
    private final BizReportMapper reportMapper;
    private final AuditRecordService auditRecordService;

    @GetMapping("/stats")
    @SaCheckPermission("dashboard:view")
    public Result<Map<String, Object>> stats() {
        Map<String, Object> data = new LinkedHashMap<>();

        if (StpUtil.hasPermission("article:list")) {
            // 管理员：平台全局
            data.put("scope", "admin");
            data.put("userCount", userMapper.selectCount(null));
            data.put("articleCount", articleMapper.selectCount(null));
            data.put("draftCount", countByStatus(null, 0));
            data.put("pendingCount", countByStatus(null, 1));
            data.put("publishedCount", countByStatus(null, 2));
            data.put("rejectedCount", countByStatus(null, 3));
            data.put("blockedCount", countByStatus(null, 4));
            // 人机协同效果：判定分布 + 改判率（管理员看全局）
            data.put("agentStats", auditRecordService.stats());
        } else if (StpUtil.hasPermission("audit:workbench")) {
            // 审核员：任务视角
            data.put("scope", "reviewer");
            data.put("pendingCount", countByStatus(null, 1));
            data.put("pendingReportCount", reportMapper.selectCount(
                    Wrappers.<BizReport>lambdaQuery().eq(BizReport::getStatus, 0)));
            data.put("todaySubmittedCount", articleMapper.selectCount(
                    Wrappers.<BizArticle>lambdaQuery()
                            .ge(BizArticle::getCreateTime, LocalDate.now().atStartOfDay())));
            data.put("agentStats", auditRecordService.stats());
        } else {
            // 创作者：个人视角（只统计自己的稿件）
            long me = StpUtil.getLoginIdAsLong();
            data.put("scope", "creator");
            data.put("myArticleCount", countByStatus(me, null));
            data.put("myDraftCount", countByStatus(me, 0));
            data.put("myPendingCount", countByStatus(me, 1));
            data.put("myPublishedCount", countByStatus(me, 2));
            data.put("myRejectedCount", countByStatus(me, 3));
        }
        return Result.ok(data);
    }

    /**
     * 统计稿件数量。
     *
     * @param authorId 为空表示统计全站，否则只统计该作者的
     * @param status   为空表示不限状态
     */
    private Long countByStatus(Long authorId, Integer status) {
        return articleMapper.selectCount(Wrappers.<BizArticle>lambdaQuery()
                .eq(authorId != null, BizArticle::getAuthorId, authorId)
                .eq(status != null, BizArticle::getStatus, status));
    }
}

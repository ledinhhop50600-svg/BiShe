package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.zimeiti.common.Result;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.mapper.BizArticleMapper;
import com.zimeiti.mapper.SysUserMapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 数据看板接口。
 * <p>阶段 2 先提供最基础的统计数字（用户数、稿件数、各状态稿件数），
 * 让首页有真实数据可显示；图表与趋势分析在阶段 3 随内容管理一起完善。
 */
@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final SysUserMapper userMapper;
    private final BizArticleMapper articleMapper;

    @GetMapping("/stats")
    @SaCheckPermission("dashboard:view")
    public Result<Map<String, Object>> stats() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("userCount", userMapper.selectCount(null));
        data.put("articleCount", articleMapper.selectCount(null));
        data.put("draftCount", countByStatus(0));
        data.put("pendingCount", countByStatus(1));
        data.put("publishedCount", countByStatus(2));
        data.put("rejectedCount", countByStatus(3));
        data.put("blockedCount", countByStatus(4));
        return Result.ok(data);
    }

    private Long countByStatus(int status) {
        return articleMapper.selectCount(
                Wrappers.<BizArticle>lambdaQuery().eq(BizArticle::getStatus, status));
    }
}

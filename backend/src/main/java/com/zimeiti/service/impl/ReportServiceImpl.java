package com.zimeiti.service.impl;

import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zimeiti.common.BizException;
import com.zimeiti.common.PageResult;
import com.zimeiti.dto.ReportHandleDTO;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.entity.BizReport;
import com.zimeiti.mapper.BizArticleMapper;
import com.zimeiti.mapper.BizReportMapper;
import com.zimeiti.mapper.SysUserMapper;
import com.zimeiti.service.ReportService;
import com.zimeiti.vo.ReportVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 举报服务实现。
 * <p>举报成立后会自动把稿件状态改为"已下架" —— 这是内容发布后的最后一道兜底。
 */
@Service
@RequiredArgsConstructor
public class ReportServiceImpl implements ReportService {

    private static final int REPORT_PENDING = 0;
    private static final int REPORT_VALID = 1;
    private static final int REPORT_INVALID = 2;
    private static final int ARTICLE_PUBLISHED = 2;
    private static final int ARTICLE_OFFLINE = 5;

    private final BizReportMapper reportMapper;
    private final BizArticleMapper articleMapper;
    private final SysUserMapper userMapper;

    @Override
    public PageResult<ReportVO> page(long current, long size, Integer status) {
        Page<BizReport> page = reportMapper.selectPage(new Page<>(current, size),
                Wrappers.<BizReport>lambdaQuery()
                        .eq(status != null, BizReport::getStatus, status)
                        .orderByAsc(BizReport::getStatus)
                        .orderByDesc(BizReport::getCreateTime));
        List<ReportVO> records = new ArrayList<>();
        for (BizReport report : page.getRecords()) {
            records.add(toVO(report));
        }
        return PageResult.of(records, page.getTotal(), page.getCurrent(), page.getSize());
    }

    @Override
    public void create(Long articleId, String reason) {
        if (!StringUtils.hasText(reason)) {
            throw new BizException("请填写举报理由");
        }
        BizArticle article = articleMapper.selectById(articleId);
        if (article == null) {
            throw new BizException("稿件不存在");
        }
        if (article.getStatus() != ARTICLE_PUBLISHED) {
            throw new BizException("只能举报已发布的稿件");
        }
        long me = StpUtil.getLoginIdAsLong();
        if (article.getAuthorId() == me) {
            throw new BizException("不能举报自己的稿件");
        }
        // 同一人不能对同一篇稿件重复举报（避免刷举报）
        Long exists = reportMapper.selectCount(Wrappers.<BizReport>lambdaQuery()
                .eq(BizReport::getArticleId, articleId)
                .eq(BizReport::getReporterId, me)
                .eq(BizReport::getStatus, REPORT_PENDING));
        if (exists != null && exists > 0) {
            throw new BizException("你已经举报过这篇稿件，正在等待处理");
        }

        BizReport report = new BizReport();
        report.setArticleId(articleId);
        report.setReporterId(me);
        report.setReason(reason);
        report.setStatus(REPORT_PENDING);
        reportMapper.insert(report);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void handle(Long id, ReportHandleDTO dto) {
        BizReport report = reportMapper.selectById(id);
        if (report == null) {
            throw new BizException("举报记录不存在");
        }
        if (report.getStatus() != REPORT_PENDING) {
            throw new BizException("该举报已处理过");
        }
        if (dto.getStatus() == null || (dto.getStatus() != REPORT_VALID && dto.getStatus() != REPORT_INVALID)) {
            throw new BizException("处理结果只能是 1（成立）或 2（不成立）");
        }

        BizReport update = new BizReport();
        update.setId(id);
        update.setStatus(dto.getStatus());
        update.setHandlerId(StpUtil.getLoginIdAsLong());
        update.setHandleRemark(dto.getRemark());
        update.setHandleTime(LocalDateTime.now());
        reportMapper.updateById(update);

        // 举报成立：稿件下架
        if (dto.getStatus() == REPORT_VALID) {
            BizArticle article = articleMapper.selectById(report.getArticleId());
            if (article != null && article.getStatus() == ARTICLE_PUBLISHED) {
                BizArticle articleUpdate = new BizArticle();
                articleUpdate.setId(article.getId());
                articleUpdate.setStatus(ARTICLE_OFFLINE);
                articleMapper.updateById(articleUpdate);
            }
        }
    }

    private ReportVO toVO(BizReport report) {
        ReportVO vo = new ReportVO();
        vo.setId(report.getId());
        vo.setArticleId(report.getArticleId());
        vo.setReporterId(report.getReporterId());
        vo.setReason(report.getReason());
        vo.setStatus(report.getStatus());
        vo.setHandlerId(report.getHandlerId());
        vo.setHandleRemark(report.getHandleRemark());
        vo.setHandleTime(report.getHandleTime());
        vo.setCreateTime(report.getCreateTime());

        BizArticle article = articleMapper.selectById(report.getArticleId());
        vo.setArticleTitle(article == null ? "（稿件已删除）" : article.getTitle());
        var reporter = userMapper.selectById(report.getReporterId());
        vo.setReporterName(reporter == null ? null : reporter.getNickname());
        if (report.getHandlerId() != null) {
            var handler = userMapper.selectById(report.getHandlerId());
            vo.setHandlerName(handler == null ? null : handler.getNickname());
        }
        return vo;
    }
}

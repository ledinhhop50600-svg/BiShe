package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.zimeiti.common.PageResult;
import com.zimeiti.common.Result;
import com.zimeiti.service.AuditRecordService;
import com.zimeiti.vo.AuditRecordVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 审核记录接口（审核记录页）。
 * <p>只对具备 audit:record 的角色开放（审核员与管理员）。
 */
@RestController
@RequestMapping("/api/audit-record")
@RequiredArgsConstructor
public class AuditRecordController {

    private final AuditRecordService auditRecordService;

    @GetMapping("/page")
    @SaCheckPermission("audit:record")
    public Result<PageResult<AuditRecordVO>> page(
            @RequestParam(defaultValue = "1") long pageNum,
            @RequestParam(defaultValue = "10") long pageSize,
            @RequestParam(required = false) Integer triggerType,
            @RequestParam(required = false) Integer riskLevel,
            @RequestParam(required = false) Boolean onlyOverride) {
        return Result.ok(auditRecordService.page(pageNum, pageSize, triggerType, riskLevel, onlyOverride));
    }

    @GetMapping("/stats")
    @SaCheckPermission("audit:record")
    public Result<Map<String, Object>> stats() {
        return Result.ok(auditRecordService.stats());
    }
}

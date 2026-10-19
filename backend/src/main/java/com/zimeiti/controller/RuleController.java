package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.annotation.SaMode;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.Result;
import com.zimeiti.entity.AuditRule;
import com.zimeiti.mapper.AuditRuleMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 审核规则只读接口。
 * <p>用途：① 对比实验脚本需要拿到规则清单，自行组装请求直接调用智能体；
 * ② 后续「审核规则库」页面（阶段 5/7）的列表数据来源。
 * <p>说明：逻辑极薄（一条查询），不单独建 service 层；规则的增删改在规则库页面时再补。
 */
@RestController
@RequestMapping("/api/rule")
@RequiredArgsConstructor
public class RuleController {

    private final AuditRuleMapper ruleMapper;

    @GetMapping("/list")
    @SaCheckPermission(value = {"article:list", "audit:workbench", "audit:rule"}, mode = SaMode.OR)
    public Result<List<AuditRule>> list() {
        List<AuditRule> rules = ruleMapper.selectList(Wrappers.<AuditRule>lambdaQuery()
                .eq(AuditRule::getEnabled, 1)
                .orderByAsc(AuditRule::getId));
        return Result.ok(rules);
    }
}

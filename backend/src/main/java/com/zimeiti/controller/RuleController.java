package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.annotation.SaMode;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.BizException;
import com.zimeiti.common.Result;
import com.zimeiti.entity.AuditRule;
import com.zimeiti.mapper.AuditRuleMapper;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 审核规则接口。
 * <p>用途：① 对比实验脚本需要拿到启用规则清单，自行组装请求直接调用智能体；
 * ② 「审核规则库」页面的列表与管理员维护入口。
 * <p>规则变更后下一次审核/预检立即生效；删除规则不会删除历史 audit_record 里的规则编号。
 */
@RestController
@RequestMapping("/api/rule")
@RequiredArgsConstructor
public class RuleController {

    private final AuditRuleMapper ruleMapper;

    @GetMapping("/all")
    @SaCheckPermission("audit:rule")
    public Result<List<AuditRule>> all() {
        return Result.ok(ruleMapper.selectList(Wrappers.<AuditRule>lambdaQuery()
                .orderByAsc(AuditRule::getId)));
    }

    @GetMapping("/list")
    @SaCheckPermission(value = {"article:list", "audit:workbench", "audit:rule"}, mode = SaMode.OR)
    public Result<List<AuditRule>> list() {
        List<AuditRule> rules = ruleMapper.selectList(Wrappers.<AuditRule>lambdaQuery()
                .eq(AuditRule::getEnabled, 1)
                .orderByAsc(AuditRule::getId));
        return Result.ok(rules);
    }

    @PostMapping
    @SaCheckPermission("audit:rule")
    public Result<Void> save(@Valid @RequestBody AuditRule rule) {
        assertCodeFree(rule.getRuleCode(), null);
        rule.setId(null);
        ruleMapper.insert(rule);
        return Result.ok();
    }

    @PutMapping
    @SaCheckPermission("audit:rule")
    public Result<Void> update(@Valid @RequestBody AuditRule rule) {
        if (rule.getId() == null) {
            throw new BizException("缺少规则 id");
        }
        if (ruleMapper.selectById(rule.getId()) == null) {
            throw new BizException("规则不存在");
        }
        assertCodeFree(rule.getRuleCode(), rule.getId());
        ruleMapper.updateById(rule);
        return Result.ok();
    }

    @DeleteMapping("/{id}")
    @SaCheckPermission("audit:rule")
    public Result<Void> delete(@PathVariable Long id) {
        if (ruleMapper.selectById(id) == null) {
            throw new BizException("规则不存在");
        }
        ruleMapper.deleteById(id);
        return Result.ok();
    }

    private void assertCodeFree(String ruleCode, Long excludeId) {
        Long count = ruleMapper.selectCount(Wrappers.<AuditRule>lambdaQuery()
                .eq(AuditRule::getRuleCode, ruleCode)
                .ne(excludeId != null, AuditRule::getId, excludeId));
        if (count != null && count > 0) {
            throw new BizException("规则编号已存在：" + ruleCode);
        }
    }
}

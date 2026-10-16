package com.zimeiti.controller;

import com.zimeiti.common.Result;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 健康检查接口。
 * <p>与业务无关，也不需要登录：一键启动脚本用它判断"后端是否已经启动完成"，
 * 前端或运维脚本也可以用它做存活探测。
 */
@RestController
public class HealthController {

    @GetMapping("/api/health")
    public Result<Map<String, Object>> health() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("status", "ok");
        data.put("service", "zimeiti-backend");
        data.put("time", LocalDateTime.now().toString());
        return Result.ok(data);
    }
}

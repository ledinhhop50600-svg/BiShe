package com.zimeiti.controller;

import com.zimeiti.common.Result;
import com.zimeiti.entity.DemoPing;
import com.zimeiti.mapper.DemoPingMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 阶段 0 链路验证接口。
 * <p>作用：证明「浏览器 → Vue 前端 → Spring Boot 接口 → MyBatis-Plus → MySQL」整条链路是通的。
 * <p>访问地址：http://localhost:8080/api/ping
 */
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class PingController {

    /** 构造器注入（Lombok 的 @RequiredArgsConstructor 自动生成构造方法），不做字段注入 */
    private final DemoPingMapper demoPingMapper;

    @GetMapping("/ping")
    public Result<Map<String, Object>> ping() {
        // selectList(null) 表示不加任何查询条件，等价于 SELECT * FROM demo_ping
        List<DemoPing> rows = demoPingMapper.selectList(null);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("count", rows.size());
        data.put("messages", rows);
        data.put("source", "数据来自 MySQL 的 demo_ping 表");
        return Result.ok(data);
    }
}

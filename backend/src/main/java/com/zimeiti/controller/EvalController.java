package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.zimeiti.common.BizException;
import com.zimeiti.common.Result;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.ObjectMapper;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 评测中心接口（管理员）。
 * <p>数据来自 `docs/eval/` 下的 JSON（由 Python 脚本生成）；页面只负责展示，
 * 不在 Java 里重算指标 —— 指标口径只有一份，避免两边算得不一样。
 * <p>「运行演示评测」会调用 `tools/eval_adaptation.py --run-id demo --out-dir docs/eval/demo`：
 *  - 结果写到 demo 目录，不覆盖论文数据；
 *  - 固定 run-id 会复用 Agent 回放缓存，第二次点通常几十秒完成；
 *  - 进程是固定命令，不接受前端传参，且只有管理员可调用。
 */
@Slf4j
@RestController
@RequestMapping("/api/eval")
@RequiredArgsConstructor
public class EvalController {

    private final ObjectMapper jsonMapper;

    @Value("${eval.project-root:..}")
    private String projectRoot;

    @Value("${eval.python:python}")
    private String python;

    /** 同一时间只允许一个评测进程，避免并发跑两份模型调用 */
    private final AtomicBoolean running = new AtomicBoolean(false);

    @GetMapping("/results")
    @SaCheckPermission("eval:manage")
    public Result<Map<String, Object>> results() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("audit", readJson("docs/eval/audit-results.json"));
        out.put("adaptation", readJson("docs/eval/adaptation-results.json"));
        out.put("demo", readJson("docs/eval/demo/adaptation-results.json"));
        out.put("performance", readJson("docs/perf/perf-latest.json"));
        out.put("speed", readJson("docs/perf/speed-experiment.json"));
        out.put("optimization", readJson("docs/perf/optimization-summary.json"));
        return Result.ok(out);
    }

    @PostMapping("/run-adaptation")
    @SaCheckPermission("eval:manage")
    public Result<Map<String, Object>> runAdaptation() {
        if (!running.compareAndSet(false, true)) {
            throw new BizException(400, "评测正在运行，请稍候");
        }
        try {
            Path root = Paths.get(projectRoot).toAbsolutePath().normalize();
            if (!Files.exists(root.resolve("tools/eval_adaptation.py"))) {
                throw new BizException(500, "找不到评测脚本：" + root.resolve("tools/eval_adaptation.py"));
            }

            ProcessBuilder pb = new ProcessBuilder(
                    python, "tools/eval_adaptation.py",
                    "--run-id", "demo",
                    "--out-dir", "docs/eval/demo");
            pb.directory(root.toFile());
            pb.redirectErrorStream(true);
            Process process = pb.start();

            StringBuilder output = new StringBuilder();
            Thread reader = new Thread(() -> drain(process, output), "eval-output-reader");
            reader.setDaemon(true);
            reader.start();

            boolean finished = process.waitFor(10, TimeUnit.MINUTES);
            if (!finished) {
                process.destroyForcibly();
                throw new BizException(500, "评测超时（10 分钟），已终止");
            }
            reader.join(3000);
            if (process.exitValue() != 0) {
                throw new BizException(500, "评测失败（退出码 " + process.exitValue() + "）：" + tail(output.toString()));
            }

            Map<String, Object> result = readJson("docs/eval/demo/adaptation-results.json");
            if (result == null) {
                throw new BizException(500, "评测完成但没有生成结果文件，请查看后端日志");
            }
            return Result.ok(result);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new BizException(500, "评测被中断");
        } catch (IOException e) {
            log.error("运行评测失败", e);
            throw new BizException(500, "评测运行失败：" + e.getMessage());
        } finally {
            running.set(false);
        }
    }

    private void drain(Process process, StringBuilder output) {
        try (BufferedReader br = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) {
                output.append(line).append('\n');
            }
        } catch (IOException e) {
            output.append("\n[读取评测输出失败] ").append(e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readJson(String relative) {
        try {
            Path path = Paths.get(projectRoot).toAbsolutePath().normalize().resolve(relative);
            if (!Files.exists(path)) {
                return null;
            }
            return jsonMapper.readValue(Files.readString(path, StandardCharsets.UTF_8), Map.class);
        } catch (Exception e) {
            log.warn("读取评测结果失败（{}）：{}", relative, e.getMessage());
            return null;
        }
    }

    private String tail(String text) {
        if (text == null) {
            return "";
        }
        int max = 800;
        return text.length() <= max ? text : text.substring(text.length() - max);
    }
}

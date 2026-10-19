package com.zimeiti.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;

import java.util.Map;

/**
 * 智能体服务的调用客户端。
 * <p>只做三件事：发请求、按需重试、把任何失败统一转成 {@link AgentUnavailableException}。
 * <p>为什么审核"重试一次"：模型服务的偶发网络抖动很常见，重试一次能明显降低失败率；
 * 但不能重试太多次 —— 审核有超时预算（30 秒），重试会把用户等待时间翻倍。
 * <p>适配**不重试**：一次适配最多 5 个平台、每个平台两次模型调用，本身就要十几秒；
 * 超时后再重试只会让用户等更久，不如直接告诉用户"稍后重试"。
 */
@Slf4j
@Component
public class AgentClient {

    private static final int AUDIT_ATTEMPTS = 2;
    private static final int ADAPT_ATTEMPTS = 2;

    private final RestClient restClient;
    private final RestClient adaptRestClient;
    private final String token;

    public AgentClient(@Qualifier("agentRestClient") RestClient restClient,
                       @Qualifier("adaptRestClient") RestClient adaptRestClient,
                       @Value("${agent.token:}") String token) {
        this.restClient = restClient;
        this.adaptRestClient = adaptRestClient;
        this.token = token;
    }

    /**
     * 调用审核接口。
     *
     * @param request 契约定义的请求体
     * @return 契约定义的响应体（键值对形式，避免为每个字段建一个 Java 类）
     * @throws AgentUnavailableException 重试后仍失败时抛出，由调用方决定如何降级
     */
    public Map<String, Object> audit(Map<String, Object> request) {
        // 审核重试所有失败（偶发网络抖动），保持原有行为
        return post(restClient, "/api/agent/audit", request,
                AUDIT_ATTEMPTS, true, false, "审核");
    }

    /**
     * 调用跨平台适配接口。
     * <p>适配**只重试"连接被拒绝"**：这类失败说明请求没有到达 Agent，重试不会重复花钱；
     * 其他失败（超时、5xx、响应为空）不重试，避免一次适配做两遍。同时强制短连接，
     * 防止 Agent 重启后复用已失效的 keep-alive 连接（实测会 0.1 秒内直接报不可用）。
     *
     * @throws AgentUnavailableException 失败时抛出，由调用方降级为"请稍后重试"
     */
    public Map<String, Object> adapt(Map<String, Object> request) {
        return post(adaptRestClient, "/api/agent/adapt", request,
                ADAPT_ATTEMPTS, false, true, "适配");
    }

    private Map<String, Object> post(RestClient client, String path, Map<String, Object> request,
                                     int maxAttempts, boolean retryAll, boolean closeConnection,
                                     String scene) {
        RuntimeException last = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                var spec = client.post()
                        .uri(path)
                        .contentType(MediaType.APPLICATION_JSON);
                if (closeConnection) {
                    spec = spec.header("Connection", "close");
                }
                if (StringUtils.hasText(token)) {
                    spec = spec.header("X-Agent-Token", token);
                }
                Map<String, Object> body = spec.body(request)
                        .retrieve()
                        .body(new ParameterizedTypeReference<Map<String, Object>>() {
                        });
                if (body == null) {
                    throw new IllegalStateException("智能体返回空响应");
                }
                return body;
            } catch (RuntimeException e) {
                last = e;
                boolean retry = attempt < maxAttempts && (retryAll || isConnectFailure(e));
                log.warn("调用智能体{}失败（第 {}/{} 次，{}）：{}", scene, attempt, maxAttempts,
                        retry ? "将重试" : "不再重试", e.getMessage());
                if (!retry) {
                    break;
                }
                if (!retryAll) {
                    // 连接被拒绝通常发生在 Agent 刚重启时，稍等再试
                    try {
                        Thread.sleep(300);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }
        throw new AgentUnavailableException(
                last == null ? "未知错误" : last.getMessage(), last);
    }

    /** 是否为"连接被拒绝"——只有这种失败能确定请求没有送达，重试是安全的 */
    private boolean isConnectFailure(Throwable e) {
        for (Throwable t = e; t != null; t = t.getCause()) {
            if (t instanceof java.net.ConnectException) {
                return true;
            }
        }
        return false;
    }

    /** 智能体不可用：网络失败、超时、5xx、响应为空等 */
    public static class AgentUnavailableException extends RuntimeException {
        public AgentUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}

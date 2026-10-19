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
    private static final int ADAPT_ATTEMPTS = 1;

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
        return post(restClient, "/api/agent/audit", request, AUDIT_ATTEMPTS, "审核");
    }

    /**
     * 调用跨平台适配接口。
     *
     * @throws AgentUnavailableException 失败时抛出，由调用方降级为"请稍后重试"
     */
    public Map<String, Object> adapt(Map<String, Object> request) {
        return post(adaptRestClient, "/api/agent/adapt", request, ADAPT_ATTEMPTS, "适配");
    }

    private Map<String, Object> post(RestClient client, String path, Map<String, Object> request,
                                     int maxAttempts, String scene) {
        RuntimeException last = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                var spec = client.post()
                        .uri(path)
                        .contentType(MediaType.APPLICATION_JSON);
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
                log.warn("调用智能体{}失败（第 {}/{} 次）：{}", scene, attempt, maxAttempts, e.getMessage());
            }
        }
        throw new AgentUnavailableException(
                last == null ? "未知错误" : last.getMessage(), last);
    }

    /** 智能体不可用：网络失败、超时、5xx、响应为空等 */
    public static class AgentUnavailableException extends RuntimeException {
        public AgentUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}

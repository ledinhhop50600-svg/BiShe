package com.zimeiti.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;

import java.util.Map;

/**
 * 智能体服务的调用客户端。
 * <p>只做三件事：发请求、重试一次、把任何失败统一转成 {@link AgentUnavailableException}。
 * <p>为什么"重试一次"：模型服务的偶发网络抖动很常见，重试一次能明显降低失败率；
 * 但不能重试太多次 —— 审核有超时预算（30 秒），重试会把用户等待时间翻倍。
 */
@Slf4j
@Component
public class AgentClient {

    private final RestClient restClient;
    private final String token;

    public AgentClient(RestClient agentRestClient,
                       @Value("${agent.token:}") String token) {
        this.restClient = agentRestClient;
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
        RuntimeException last = null;
        for (int attempt = 1; attempt <= 2; attempt++) {
            try {
                var spec = restClient.post()
                        .uri("/api/agent/audit")
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
                log.warn("调用智能体失败（第 {} 次）：{}", attempt, e.getMessage());
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

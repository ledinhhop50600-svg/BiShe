package com.zimeiti.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * 智能体服务的 HTTP 客户端配置。
 * <p>超时设计：连接 3 秒、读取 {@code agent.timeout-seconds}（默认 30 秒）。
 * 智能体内部的模型调用超时是 25 秒（见 agent/.env），比这里短 ——
 * 保证"Agent 先超时并返回明确的错误"，而不是主系统先断开、拿不到任何信息。
 */
@Configuration
public class AgentConfig {

    @Value("${agent.base-url:http://localhost:8001}")
    private String baseUrl;

    @Value("${agent.timeout-seconds:30}")
    private int timeoutSeconds;

    @Bean
    public RestClient agentRestClient() {
        return buildRestClient(timeoutSeconds * 1000);
    }

    /**
     * 适配专用客户端：读超时放宽到 120 秒。
     * <p>原因：适配一个平台要调用两次模型（改写 + 合规预检），一次请求最多 5 个平台，
     * 30 秒的审核超时不够用。审核接口仍用上面那个 30 秒的客户端 —— 两类请求的预算不同，
     * 不能共用一个超时值。
     */
    @Bean
    public RestClient adaptRestClient() {
        return buildRestClient(120_000);
    }

    private RestClient buildRestClient(int readTimeoutMillis) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(3000);
        factory.setReadTimeout(readTimeoutMillis);
        return RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(factory)
                .build();
    }
}

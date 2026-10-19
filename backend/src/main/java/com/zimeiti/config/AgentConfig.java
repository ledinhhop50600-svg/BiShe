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
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(3000);
        factory.setReadTimeout(timeoutSeconds * 1000);
        return RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(factory)
                .build();
    }
}

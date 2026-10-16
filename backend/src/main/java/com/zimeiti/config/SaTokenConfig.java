package com.zimeiti.config;

import cn.dev33.satoken.interceptor.SaInterceptor;
import cn.dev33.satoken.stp.StpUtil;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Sa-Token 配置：注册登录校验拦截器。
 * <p>作用：除白名单外的所有 /api/** 接口，都要求"已登录"才能访问。
 * 未登录访问时会抛出 NotLoginException，由全局异常处理器转换成 401 返回给前端。
 * <p>白名单里放的是"必须在未登录状态下就能访问"的接口：
 * 登录接口本身，以及健康检查接口（一键启动脚本要用它判断服务是否就绪）。
 * <p>注意：这里只做"是否登录"的校验。具体某个接口需要什么权限，用注解
 * {@code @SaCheckPermission("article:list")} 单独声明，两件事分开管。
 */
@Configuration
public class SaTokenConfig implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new SaInterceptor(handle -> StpUtil.checkLogin()))
                .addPathPatterns("/api/**")
                .excludePathPatterns(
                        "/api/health",
                        "/api/auth/login"
                );
    }
}

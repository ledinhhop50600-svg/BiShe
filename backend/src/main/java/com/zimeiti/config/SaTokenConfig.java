package com.zimeiti.config;

import cn.dev33.satoken.interceptor.SaInterceptor;
import cn.dev33.satoken.stp.StpUtil;
import com.zimeiti.common.BizException;
import com.zimeiti.entity.SysUser;
import com.zimeiti.mapper.SysUserMapper;
import lombok.RequiredArgsConstructor;
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
 * <p>2026-10-29 安全修复：只查登录态不够——账号被禁用/删除后旧令牌仍然有效。
 * 这里再查一次用户状态，发现禁用/删除立即注销并返回 401。
 * 演示规模每请求一次主键查询可以接受；生产可换缓存，但禁用时也必须同步清缓存。
 */
@Configuration
@RequiredArgsConstructor
public class SaTokenConfig implements WebMvcConfigurer {

    private final SysUserMapper userMapper;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new SaInterceptor(handle -> {
            StpUtil.checkLogin();
            long userId = StpUtil.getLoginIdAsLong();
            SysUser user = userMapper.selectById(userId);
            if (user == null || Integer.valueOf(0).equals(user.getStatus())) {
                StpUtil.logout();
                throw new BizException(401, "账号已被禁用或删除，请重新登录");
            }
        }))
                .addPathPatterns("/api/**")
                .excludePathPatterns(
                        "/api/health",
                        "/api/auth/login",
                        "/api/auth/register",
                        "/api/auth/captcha"
                );
    }
}

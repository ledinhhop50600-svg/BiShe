package com.zimeiti.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * 密码加密配置。
 * <p>用 BCrypt 对密码做加盐哈希后存库：数据库里看不到明文，且同一个密码每次生成的哈希都不同，
 * 无法通过"比对哈希值"反推出密码。
 * <p>注意：这里只用 Spring Security 的加密工具类，并没有引入整套 Spring Security 框架。
 */
@Configuration
public class PasswordConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}

package com.zimeiti;

import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

/**
 * 生成种子数据用的密码哈希。
 * <p>这不是一个"测试"，而是开发期的一次性工具：把演示账号的初始密码
 * （统一为 123456）用 BCrypt 算成哈希，写进 db/03_seed.sql。
 * <p>BCrypt 每次生成的哈希都不同（内含随机盐），所以只需要生成一次，所有演示账号共用同一个哈希即可。
 */
public class PasswordHashPrinter {

    @Test
    void printHash() {
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
        String raw = "123456";
        String hash = encoder.encode(raw);
        System.out.println("BCRYPT_HASH_START");
        System.out.println(hash);
        System.out.println("BCRYPT_HASH_END");
        System.out.println("SELF_CHECK=" + encoder.matches(raw, hash));
    }
}

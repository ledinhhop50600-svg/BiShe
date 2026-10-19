package com.zimeiti.common;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/**
 * 稿件内容指纹。
 * <p>用途：把智能体审核记录绑定到"具体这一版内容"。
 * 审核员看到一条结论时，必须先确认稿件从那以后没有被改过 ——
 * 用 `update_time` 比较会在"同一秒内修改并重提"时失效（DATETIME 默认只到秒），
 * 而内容哈希不受时间精度影响。
 */
public final class ContentHash {

    private ContentHash() {
    }

    public static String of(String title, String content) {
        String raw = (title == null ? "" : title) + "\n" + (content == null ? "" : content);
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(md.digest(raw.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            // JDK 必然支持 SHA-256，这里只是编译期要求
            throw new IllegalStateException("SHA-256 不可用", e);
        }
    }
}

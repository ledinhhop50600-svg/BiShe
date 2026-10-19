package com.zimeiti.service;

import com.zimeiti.common.BizException;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 图形验证码（算式形式）。
 * <p>为什么做：注册是公开接口，不加任何门槛会被脚本批量刷账号。算式的成本极低，
 * 又能体现"防刷"意识，答辩时是一个可讲的点。
 * <p>为什么放内存而不是 Redis：本项目只在本机运行，不引入 Redis（D-P5）。
 * 进程重启后验证码失效是正常行为。
 * <p>安全细节：
 *  - 答案只存在服务端，前端只拿到题目；
 *  - 一次性使用（校验时立即删除），防止同一题被反复提交；
 *  - 5 分钟过期；
 *  - 使用 SecureRandom，避免可预测的随机序列。
 */
@Service
public class CaptchaService {

    private static final long TTL_MILLIS = 5 * 60 * 1000L;
    private static final int MAX_STORE = 5000;

    private final SecureRandom random = new SecureRandom();
    private final Map<String, Entry> store = new ConcurrentHashMap<>();

    /** 生成一道新题：返回 captchaId 与题目文本 */
    public Map<String, String> create() {
        cleanup();
        int a = 1 + random.nextInt(9);
        int b = 1 + random.nextInt(9);
        String id = UUID.randomUUID().toString();
        store.put(id, new Entry(String.valueOf(a + b), System.currentTimeMillis() + TTL_MILLIS));

        Map<String, String> out = new LinkedHashMap<>();
        out.put("captchaId", id);
        out.put("question", a + " + " + b + " = ?");
        return out;
    }

    /** 校验并立即作废；失败抛出 400，前端提示刷新 */
    public void verify(String captchaId, String answer) {
        if (captchaId == null || answer == null) {
            throw new BizException(400, "请填写验证码");
        }
        Entry entry = store.remove(captchaId);
        if (entry == null) {
            throw new BizException(400, "验证码已失效，请刷新后重试");
        }
        if (entry.expireAt < System.currentTimeMillis()) {
            throw new BizException(400, "验证码已过期，请刷新后重试");
        }
        if (!entry.answer.equals(answer.trim())) {
            throw new BizException(400, "验证码错误");
        }
    }

    /** 顺手清理过期条目；数量异常时直接清空，避免内存被刷爆 */
    private void cleanup() {
        long now = System.currentTimeMillis();
        store.entrySet().removeIf(e -> e.getValue().expireAt < now);
        if (store.size() > MAX_STORE) {
            store.clear();
        }
    }

    private record Entry(String answer, long expireAt) {
    }
}

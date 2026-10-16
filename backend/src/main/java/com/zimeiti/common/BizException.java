package com.zimeiti.common;

import lombok.Getter;

/**
 * 业务异常。
 * <p>业务规则不满足时（例如"账号或密码错误""该角色不允许删除"）抛出本异常，
 * 由 {@link GlobalExceptionHandler} 统一捕获并转换成 Result 返回给前端。
 * <p>这样做的好处：业务代码里不用写一堆 if-else 去拼返回值，只负责"抛"，格式统一由一处处理。
 */
@Getter
public class BizException extends RuntimeException {

    private final int code;

    public BizException(String message) {
        this(500, message);
    }

    public BizException(int code, String message) {
        super(message);
        this.code = code;
    }
}

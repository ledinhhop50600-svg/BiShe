package com.zimeiti.common;

import lombok.Data;

/**
 * 统一响应体。
 * <p>全站所有接口都返回这个结构，前端只需判断 code 是否为 200，不用为每个接口单独写解析逻辑。
 *
 * @param <T> 业务数据类型
 */
@Data
public class Result<T> {

    /** 状态码：200 成功；401 未登录；403 无权限；500 业务或系统错误 */
    private int code;

    /** 提示信息 */
    private String msg;

    /** 业务数据 */
    private T data;

    public static <T> Result<T> ok(T data) {
        Result<T> r = new Result<>();
        r.code = 200;
        r.msg = "success";
        r.data = data;
        return r;
    }

    public static <T> Result<T> ok() {
        return ok(null);
    }

    public static <T> Result<T> fail(String msg) {
        return fail(500, msg);
    }

    public static <T> Result<T> fail(int code, String msg) {
        Result<T> r = new Result<>();
        r.code = code;
        r.msg = msg;
        return r;
    }
}

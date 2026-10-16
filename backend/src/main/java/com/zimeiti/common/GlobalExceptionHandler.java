package com.zimeiti.common;

import cn.dev33.satoken.exception.NotLoginException;
import cn.dev33.satoken.exception.NotPermissionException;
import cn.dev33.satoken.exception.NotRoleException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * 全局异常处理器。
 * <p>把各类异常统一转换成 {@link Result} 返回，避免每个接口各写一套 try-catch，
 * 也避免把 Java 异常堆栈直接暴露给前端。
 * <p>处理顺序说明：越具体的异常越先匹配 —— 业务异常给前端看具体原因，
 * 未登录返回 401 让前端跳登录页，未知异常只返回一句通用提示并记日志。
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /** 业务异常：直接把提示信息返回给前端 */
    @ExceptionHandler(BizException.class)
    public Result<Void> handleBizException(BizException e) {
        log.warn("业务异常：{}", e.getMessage());
        return Result.fail(e.getCode(), e.getMessage());
    }

    /** 未登录：返回 401，前端拦截器据此跳转登录页 */
    @ExceptionHandler(NotLoginException.class)
    public Result<Void> handleNotLogin(NotLoginException e) {
        log.warn("未登录访问：{}", e.getMessage());
        return Result.fail(401, "登录状态已失效，请重新登录");
    }

    /** 无权限：返回 403 */
    @ExceptionHandler({NotPermissionException.class, NotRoleException.class})
    public Result<Void> handleNoPermission(Exception e) {
        log.warn("权限不足：{}", e.getMessage());
        return Result.fail(403, "没有操作权限");
    }

    /** 参数校验失败（@Valid 注解触发），取第一条错误信息返回 */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValidation(MethodArgumentNotValidException e) {
        FieldError fieldError = e.getBindingResult().getFieldError();
        String msg = fieldError != null ? fieldError.getDefaultMessage() : "参数不合法";
        log.warn("参数校验失败：{}", msg);
        return Result.fail(400, msg);
    }

    /** 兜底：其它未预料到的异常。日志里留完整堆栈，返回给前端的只有一句通用提示 */
    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception e) {
        log.error("系统异常", e);
        return Result.fail(500, "系统繁忙，请稍后重试");
    }
}

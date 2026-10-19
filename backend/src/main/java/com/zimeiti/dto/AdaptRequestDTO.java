package com.zimeiti.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * 跨平台适配请求。
 * <p>只传目标平台标识，稿件内容由后端按 id 读取 ——
 * 不能让前端把正文传上来，否则等于允许适配任意文本，与"源自本系统稿件"的定位不符。
 */
@Data
public class AdaptRequestDTO {

    @NotEmpty(message = "请至少选择一个目标平台")
    @Size(max = 5, message = "一次最多适配 5 个平台")
    private List<@NotBlank(message = "平台标识不能为空") String> platformKeys;
}

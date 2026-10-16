package com.zimeiti.common;

import lombok.Data;

import java.util.List;

/**
 * 分页结果封装。
 * <p>所有列表接口需要分页时都返回这个结构，前端表格组件直接取 records 作为数据源、total 作为总数。
 *
 * @param <T> 列表元素类型
 */
@Data
public class PageResult<T> {

    /** 当前页数据 */
    private List<T> records;

    /** 总条数 */
    private long total;

    /** 当前页码（从 1 开始） */
    private long current;

    /** 每页条数 */
    private long size;

    public static <T> PageResult<T> of(List<T> records, long total, long current, long size) {
        PageResult<T> r = new PageResult<>();
        r.records = records;
        r.total = total;
        r.current = current;
        r.size = size;
        return r;
    }
}

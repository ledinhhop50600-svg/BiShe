package com.zimeiti.service;

import com.zimeiti.entity.BizCategory;
import com.zimeiti.entity.BizTag;

import java.util.List;

/**
 * 分类与标签服务。
 * <p>两者都属于"内容分类体系"，管理界面也在一起，所以放在同一个服务里 —— 不必为了对称硬拆两个。
 */
public interface CategoryService {

    List<BizCategory> listCategories();

    void saveCategory(BizCategory category);

    void updateCategory(BizCategory category);

    void deleteCategory(Long id);

    List<BizTag> listTags();

    void saveTag(BizTag tag);

    void updateTag(BizTag tag);

    void deleteTag(Long id);
}

package com.zimeiti.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.BizException;
import com.zimeiti.entity.BizArticle;
import com.zimeiti.entity.BizArticleTag;
import com.zimeiti.entity.BizCategory;
import com.zimeiti.entity.BizTag;
import com.zimeiti.mapper.BizArticleMapper;
import com.zimeiti.mapper.BizArticleTagMapper;
import com.zimeiti.mapper.BizCategoryMapper;
import com.zimeiti.mapper.BizTagMapper;
import com.zimeiti.service.CategoryService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * 分类与标签服务实现。
 * <p>删除保护：分类被稿件引用、标签被稿件关联时不允许删除，避免稿件失去分类/标签后数据"悬空"。
 */
@Service
@RequiredArgsConstructor
public class CategoryServiceImpl implements CategoryService {

    private final BizCategoryMapper categoryMapper;
    private final BizTagMapper tagMapper;
    private final BizArticleMapper articleMapper;
    private final BizArticleTagMapper articleTagMapper;

    @Override
    public List<BizCategory> listCategories() {
        return categoryMapper.selectList(Wrappers.<BizCategory>lambdaQuery()
                .orderByAsc(BizCategory::getSort)
                .orderByAsc(BizCategory::getId));
    }

    @Override
    public void saveCategory(BizCategory category) {
        category.setId(null);
        checkCategoryName(category.getName(), null);
        if (category.getStatus() == null) {
            category.setStatus(1);
        }
        categoryMapper.insert(category);
    }

    @Override
    public void updateCategory(BizCategory category) {
        if (category.getId() == null) {
            throw new BizException("缺少分类 id");
        }
        checkCategoryName(category.getName(), category.getId());
        categoryMapper.updateById(category);
    }

    @Override
    public void deleteCategory(Long id) {
        BizCategory category = categoryMapper.selectById(id);
        if (category == null) {
            throw new BizException("分类不存在");
        }
        Long used = articleMapper.selectCount(
                Wrappers.<BizArticle>lambdaQuery().eq(BizArticle::getCategoryId, id));
        if (used != null && used > 0) {
            throw new BizException("该分类下还有 " + used + " 篇稿件，请先调整这些稿件的分类");
        }
        categoryMapper.deleteById(id);
    }

    @Override
    public List<BizTag> listTags() {
        return tagMapper.selectList(Wrappers.<BizTag>lambdaQuery().orderByAsc(BizTag::getId));
    }

    @Override
    public void saveTag(BizTag tag) {
        tag.setId(null);
        checkTagName(tag.getName(), null);
        tagMapper.insert(tag);
    }

    @Override
    public void updateTag(BizTag tag) {
        if (tag.getId() == null) {
            throw new BizException("缺少标签 id");
        }
        checkTagName(tag.getName(), tag.getId());
        tagMapper.updateById(tag);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteTag(Long id) {
        BizTag tag = tagMapper.selectById(id);
        if (tag == null) {
            throw new BizException("标签不存在");
        }
        // 标签与稿件是多对多：删除标签时一并清掉关联，不影响稿件本身
        articleTagMapper.delete(Wrappers.<BizArticleTag>lambdaQuery().eq(BizArticleTag::getTagId, id));
        tagMapper.deleteById(id);
    }

    private void checkCategoryName(String name, Long excludeId) {
        Long count = categoryMapper.selectCount(Wrappers.<BizCategory>lambdaQuery()
                .eq(BizCategory::getName, name)
                .ne(excludeId != null, BizCategory::getId, excludeId));
        if (count != null && count > 0) {
            throw new BizException("分类名称已存在：" + name);
        }
    }

    private void checkTagName(String name, Long excludeId) {
        Long count = tagMapper.selectCount(Wrappers.<BizTag>lambdaQuery()
                .eq(BizTag::getName, name)
                .ne(excludeId != null, BizTag::getId, excludeId));
        if (count != null && count > 0) {
            throw new BizException("标签已存在：" + name);
        }
    }
}

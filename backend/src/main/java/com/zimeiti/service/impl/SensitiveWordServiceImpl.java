package com.zimeiti.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zimeiti.common.BizException;
import com.zimeiti.common.PageResult;
import com.zimeiti.entity.AuditSensitiveWord;
import com.zimeiti.mapper.AuditSensitiveWordMapper;
import com.zimeiti.service.SensitiveWordService;
import com.zimeiti.vo.SensitiveCheckVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.List;

/**
 * 敏感词服务实现。
 */
@Service
@RequiredArgsConstructor
public class SensitiveWordServiceImpl implements SensitiveWordService {

    private final AuditSensitiveWordMapper wordMapper;

    @Override
    public PageResult<AuditSensitiveWord> page(long current, long size, String word, String category) {
        Page<AuditSensitiveWord> page = wordMapper.selectPage(new Page<>(current, size),
                Wrappers.<AuditSensitiveWord>lambdaQuery()
                        .like(StringUtils.hasText(word), AuditSensitiveWord::getWord, word)
                        .eq(StringUtils.hasText(category), AuditSensitiveWord::getCategory, category)
                        .orderByAsc(AuditSensitiveWord::getCategory)
                        .orderByAsc(AuditSensitiveWord::getId));
        return PageResult.of(page.getRecords(), page.getTotal(), page.getCurrent(), page.getSize());
    }

    @Override
    public void save(AuditSensitiveWord word) {
        word.setId(null);
        checkDuplicate(word.getWord(), null);
        if (word.getEnabled() == null) {
            word.setEnabled(1);
        }
        wordMapper.insert(word);
    }

    @Override
    public void update(AuditSensitiveWord word) {
        if (word.getId() == null) {
            throw new BizException("缺少敏感词 id");
        }
        checkDuplicate(word.getWord(), word.getId());
        wordMapper.updateById(word);
    }

    @Override
    public void delete(Long id) {
        if (wordMapper.selectById(id) == null) {
            throw new BizException("敏感词不存在");
        }
        wordMapper.deleteById(id);
    }

    /**
     * 敏感词检测：朴素子串匹配。
     * <p>实现说明（答辩要能讲清它的局限）：
     *  - 只做"文中是否包含某个词"，**不理解语境**。例如作品名《最好的我们》会被误判为绝对化用语，
     *    而"全网最好的产品"才是真正的违规表述 —— 关键词匹配区分不了这两者。
     *  - 复杂度是"词数 × 文本长度"，在几十个词、几千字的规模下完全够用，不需要 AC 自动机之类的优化。
     *  - 这个局限正是引入智能体的动机，也是后续对比实验要量化展示的差距。
     */
    @Override
    public SensitiveCheckVO check(String text) {
        SensitiveCheckVO vo = new SensitiveCheckVO();
        if (!StringUtils.hasText(text)) {
            vo.setPassed(true);
            vo.setMessage("内容为空，无需检测");
            return vo;
        }

        List<AuditSensitiveWord> words = wordMapper.selectList(
                Wrappers.<AuditSensitiveWord>lambdaQuery().eq(AuditSensitiveWord::getEnabled, 1));

        int maxLevel = 0;
        for (AuditSensitiveWord w : words) {
            if (text.contains(w.getWord())) {
                vo.getMatched().add(w.getWord());
                if (!vo.getCategories().contains(w.getCategory())) {
                    vo.getCategories().add(w.getCategory());
                }
                if (w.getLevel() != null && w.getLevel() > maxLevel) {
                    maxLevel = w.getLevel();
                }
            }
        }

        vo.setMaxLevel(maxLevel);
        vo.setPassed(vo.getMatched().isEmpty());
        if (vo.getMatched().isEmpty()) {
            vo.setMessage("未命中任何敏感词");
        } else {
            String levelText = switch (maxLevel) {
                case 3 -> "严重";
                case 2 -> "违规";
                case 1 -> "疑似";
                default -> "未知";
            };
            vo.setMessage("命中 " + vo.getMatched().size() + " 个敏感词，最高等级：" + levelText
                    + "（关键词匹配不理解语境，结论仅供参考）");
        }
        return vo;
    }

    private void checkDuplicate(String word, Long excludeId) {
        Long count = wordMapper.selectCount(Wrappers.<AuditSensitiveWord>lambdaQuery()
                .eq(AuditSensitiveWord::getWord, word)
                .ne(excludeId != null, AuditSensitiveWord::getId, excludeId));
        if (count != null && count > 0) {
            throw new BizException("该敏感词已存在：" + word);
        }
    }
}

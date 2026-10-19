package com.zimeiti.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.BizException;
import com.zimeiti.entity.AuditPlatform;
import com.zimeiti.mapper.AuditPlatformMapper;
import com.zimeiti.service.PlatformService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 目标平台服务实现。
 */
@Service
@RequiredArgsConstructor
public class PlatformServiceImpl implements PlatformService {

    private final AuditPlatformMapper platformMapper;

    @Override
    public List<AuditPlatform> list() {
        return platformMapper.selectList(Wrappers.<AuditPlatform>lambdaQuery()
                .orderByAsc(AuditPlatform::getSort)
                .orderByAsc(AuditPlatform::getId));
    }

    @Override
    public void save(AuditPlatform platform) {
        platform.setId(null);
        checkKey(platform.getPlatformKey(), null);
        if (platform.getStatus() == null) {
            platform.setStatus(1);
        }
        platformMapper.insert(platform);
    }

    @Override
    public void update(AuditPlatform platform) {
        if (platform.getId() == null) {
            throw new BizException("缺少平台 id");
        }
        checkKey(platform.getPlatformKey(), platform.getId());
        platformMapper.updateById(platform);
    }

    @Override
    public void delete(Long id) {
        AuditPlatform platform = platformMapper.selectById(id);
        if (platform == null) {
            throw new BizException("平台不存在");
        }
        // 本平台（local）是内容发布的目标，不允许删除
        if ("local".equals(platform.getPlatformKey())) {
            throw new BizException("「本平台」是内容发布的默认目标，不能删除");
        }
        platformMapper.deleteById(id);
    }

    private void checkKey(String platformKey, Long excludeId) {
        Long count = platformMapper.selectCount(Wrappers.<AuditPlatform>lambdaQuery()
                .eq(AuditPlatform::getPlatformKey, platformKey)
                .ne(excludeId != null, AuditPlatform::getId, excludeId));
        if (count != null && count > 0) {
            throw new BizException("平台标识已存在：" + platformKey);
        }
    }
}

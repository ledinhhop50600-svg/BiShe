<script setup>
import { useRoute } from 'vue-router'

/**
 * 后续阶段页面的统一占位页。
 * <p>为什么要占位：菜单是从数据库下发的，包含了内容管理、审核中心等后续阶段的入口。
 * 如果点进去是空白或 404，演示时会显得系统不完整；用一个占位页说明"该模块计划在第几阶段实现"，
 * 既能自圆其说，也方便向导师说明开发进度。
 */
const route = useRoute()
</script>

<template>
  <el-card shadow="never">
    <el-result icon="info" :title="`「${route.meta?.title || '该模块'}」尚未开发`">
      <template #sub-title>
        <p>这个模块已在菜单与权限体系中配置好，但功能将在后续阶段实现。</p>
        <p class="stage">{{ route.meta?.title }} —— 见《阶段划分》文档</p>
      </template>
      <template #extra>
        <el-alert type="info" :closable="false">
          <template #title>
            当前已完成：环境与骨架（阶段 0）、数据库与登录认证（阶段 1）、权限管理与后台框架（阶段 2）。
          </template>
        </el-alert>
      </template>
    </el-result>
  </el-card>
</template>

<style scoped>
.stage {
  color: #909399;
  font-size: 13px;
}
</style>

<script setup>
/**
 * 侧边栏菜单项（递归组件）。
 * <p>菜单是树形结构（目录下可以再有菜单），所以用一个会调用自己的组件来渲染：
 * 有子节点就渲染成"可展开的子菜单"，没有子节点就渲染成"可点击的菜单项"。
 * <p>能渲染出什么完全取决于数据库下发的菜单数据 —— 换一个角色登录，这里的结构就不同。
 */
defineProps({
  item: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <el-sub-menu v-if="item.children && item.children.length" :index="String(item.id)">
    <template #title>
      <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
      <span>{{ item.menuName }}</span>
    </template>
    <SidebarItem v-for="child in item.children" :key="child.id" :item="child" />
  </el-sub-menu>

  <el-menu-item v-else :index="item.path">
    <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
    <template #title>{{ item.menuName }}</template>
  </el-menu-item>
</template>

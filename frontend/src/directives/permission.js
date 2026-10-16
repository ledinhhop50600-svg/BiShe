import { useUserStore } from '@/stores/user'

/**
 * 按钮级权限指令：v-perm="'article:edit'"
 * <p>用法：给按钮加上该指令，当前用户没有这个权限标识时，按钮会被直接从 DOM 中移除。
 * <p>效果举例：审核员登录看不到"删除用户"按钮，管理员能看到。
 * <p>重要提醒：这只是"体验层"的控制 —— 让没有权限的人看不到入口。
 * 真正的安全边界在后端的 @SaCheckPermission，即使有人手工拼接口调用也会被拒绝。
 */
export const permission = {
  mounted(el, binding) {
    const perm = binding.value
    if (!perm) {
      return
    }
    const userStore = useUserStore()
    if (!userStore.hasPermission(perm)) {
      // 没有权限：把元素从页面上摘掉
      el.parentNode && el.parentNode.removeChild(el)
    }
  },
}

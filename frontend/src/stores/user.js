import { defineStore } from 'pinia'
import { getCurrentUser, login as loginApi, logout as logoutApi, register as registerApi } from '@/api/auth'
import { clearToken, getToken, saveToken } from '@/api/request'

/**
 * 登录用户状态。
 * <p>存三样东西：令牌、用户信息（含角色/权限/菜单）。
 * <p>为什么要有这个 store：多个页面都要用到"我是谁、我有什么权限、我能看到哪些菜单"，
 * 放在这里集中管理，避免每个页面各请求一遍、各存一份。
 */
export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken() || '',
    userInfo: null,
  }),

  getters: {
    /** 是否已登录 */
    isLogin: (state) => !!state.token,
    /** 角色标识，如 ['reviewer'] */
    roleKeys: (state) => state.userInfo?.roleKeys || [],
    /** 权限标识列表，用于按钮级权限控制 */
    permissions: (state) => state.userInfo?.permissions || [],
    /** 菜单树，用于渲染导航 */
    menus: (state) => state.userInfo?.menus || [],
    /** 显示用的角色名称，如 ['审核员'] */
    roleNames: (state) => state.userInfo?.roles || [],
  },

  actions: {
    /** 登录：成功后保存令牌与用户信息 */
    async login(form) {
      const data = await loginApi(form)
      this.token = data.tokenValue
      this.userInfo = data.userInfo
      saveToken(data.tokenName, data.tokenValue)
      return data
    },

    /** 注册：后端固定分配创作者角色，成功后直接登录 */
    async register(form) {
      const data = await registerApi(form)
      this.token = data.tokenValue
      this.userInfo = data.userInfo
      saveToken(data.tokenName, data.tokenValue)
      return data
    },

    /** 拉取当前用户信息（刷新页面后用它恢复状态） */
    async fetchUserInfo() {
      this.userInfo = await getCurrentUser()
      return this.userInfo
    },

    /** 登出：通知后端注销令牌，并清空本地状态 */
    async logout() {
      try {
        await logoutApi()
      } catch (e) {
        // 令牌已失效时登出接口会报错，这属于正常情况，忽略即可
      }
      this.token = ''
      this.userInfo = null
      clearToken()
    },

    /** 只清本地登录态（后端令牌已失效时用，避免再调登出接口报错） */
    logoutLocal() {
      this.token = ''
      this.userInfo = null
      clearToken()
    },

    /** 按钮级权限判断：页面里用它决定按钮是否显示 */
    hasPermission(perm) {
      if (!perm) {
        return true
      }
      return this.permissions.includes(perm)
    },
  },
})

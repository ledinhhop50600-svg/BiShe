import { createApp } from 'vue'
import { createPinia } from 'pinia'

// Element Plus：UI 组件库（表格、按钮、表单等成品控件）
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// 中文语言包：让分页、日期选择器等组件显示中文
import zhCn from 'element-plus/es/locale/lang/zh-cn'
// Element Plus 图标：菜单里用到的 DataLine / Document 等图标名都来自这里
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { permission } from './directives/permission'

const app = createApp(App)

// 全局注册所有图标，模板里可以直接用 <component :is="'User'" /> 或 <el-icon><User /></el-icon>
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

// 按钮级权限指令：v-perm="'article:edit'"
app.directive('perm', permission)

// Pinia：前端状态管理（存登录用户、权限等跨页面共享的数据）
app.use(createPinia())
// Vue Router：页面路由
app.use(router)
// 全局注册 Element Plus，页面里可直接使用 <el-button> <el-table> 等标签
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const loading = ref(false)
const result = ref(null)
const error = ref('')

// 点击按钮 -> 请求后端 /api/ping -> 后端查 MySQL -> 数据回到这里渲染成表格
async function ping() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await axios.get('/api/ping')
    if (data.code === 200) {
      result.value = data.data
    } else {
      error.value = data.msg
    }
  } catch (e) {
    error.value = '请求失败：' + e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="wrap">
    <el-card>
      <h2>阶段 0 · 链路验证</h2>
      <p>点下面的按钮，它会请求后端接口，后端再从 MySQL 读数据返回。</p>

      <el-button type="primary" :loading="loading" @click="ping">点我验证链路</el-button>

      <el-alert v-if="error" :title="error" type="error" show-icon style="margin-top: 16px" />

      <div v-if="result" style="margin-top: 16px">
        <el-descriptions title="返回结果" :column="1" border>
          <el-descriptions-item label="数据条数">{{ result.count }}</el-descriptions-item>
          <el-descriptions-item label="数据来源">{{ result.source }}</el-descriptions-item>
        </el-descriptions>

        <el-table :data="result.messages" border style="margin-top: 12px">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="message" label="来自数据库的消息" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 760px;
  margin: 60px auto;
  padding: 0 16px;
}
</style>

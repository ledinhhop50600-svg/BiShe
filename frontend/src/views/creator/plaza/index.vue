<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { plazaArticles } from '@/api/article'
import { createReport } from '@/api/report'

/**
 * 内容广场（创作者）：浏览他人已发布的稿件。
 * <p>它的作用是给"举报"一个真实的入口 —— 没有浏览，就无法举报；
 * 同时也让创作者能看到同行的内容，符合自媒体平台的日常使用习惯。
 */
const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ pageNum: 1, pageSize: 9, title: '' })

const reportVisible = ref(false)
const target = ref(null)
const reason = ref('')
const submitting = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await plazaArticles(query)
    list.value = data.records
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  query.pageNum = 1
  load()
}

function openReport(item) {
  target.value = item
  reason.value = ''
  reportVisible.value = true
}

async function submitReport() {
  if (!reason.value.trim()) {
    ElMessage.warning('请填写举报理由')
    return
  }
  submitting.value = true
  try {
    await createReport(target.value.id, reason.value)
    ElMessage.success('举报已提交，等待审核员处理')
    reportVisible.value = false
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="query.title" placeholder="搜索已发布内容" clearable style="width: 220px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">搜索</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div v-loading="loading" class="grid">
      <el-empty v-if="!list.length" description="暂无已发布的内容" />
      <el-card v-for="item in list" :key="item.id" shadow="hover" class="item">
        <div class="item-title">{{ item.title }}</div>
        <div class="item-meta">
          <span>{{ item.authorName }}</span>
          <span>{{ item.categoryName || '未分类' }}</span>
        </div>
        <div class="item-summary">{{ item.summary || item.content?.slice(0, 80) + '...' }}</div>
        <div class="item-footer">
          <span class="time">{{ item.publishTime?.replace('T', ' ').slice(0, 16) }}</span>
          <el-button link type="danger" @click="openReport(item)">举报</el-button>
        </div>
      </el-card>
    </div>

    <el-pagination
      v-model:current-page="query.pageNum"
      v-model:page-size="query.pageSize"
      :total="total"
      :page-sizes="[9, 18, 36]"
      layout="total, sizes, prev, pager, next"
      class="pagination"
      @size-change="load"
      @current-change="load"
    />

    <el-dialog v-model="reportVisible" title="举报内容" width="520px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="稿件">{{ target?.title }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ target?.authorName }}</el-descriptions-item>
      </el-descriptions>
      <el-form label-width="80px" class="block">
        <el-form-item label="举报理由">
          <el-input v-model="reason" type="textarea" :rows="4" placeholder="请具体说明问题，例如：抄袭、虚假宣传、诱导引流等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="submitReport">提交举报</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 16px;
  min-height: 200px;
}

.item {
  display: flex;
  flex-direction: column;
}

.item-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 8px;
}

.item-summary {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
  height: 62px;
  overflow: hidden;
}

.item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.time {
  font-size: 12px;
  color: #c0c4cc;
}

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.block {
  margin-top: 12px;
}
</style>

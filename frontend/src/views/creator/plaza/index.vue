<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { plazaArticles } from '@/api/article'
import { listCategories, listTags } from '@/api/category'
import { createReport } from '@/api/report'
import { useUserStore } from '@/stores/user'

/**
 * 内容广场（创作者）：浏览平台已发布的内容。
 * <p>这里**包含自己发布的内容** —— 广场就是"看平台上的内容"，把自己排除在外并不合理。
 * 要限制的是"不能举报自己的内容"：界面上对自己的卡片隐藏举报按钮，后端举报接口也会二次校验。
 */
const userStore = useUserStore()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const categories = ref([])
const tags = ref([])
const query = reactive({ pageNum: 1, pageSize: 9, title: '', categoryId: null, tagId: null })

/** 是否是自己的内容：是则隐藏举报入口 */
function isMine(item) {
  return item.authorId === userStore.userInfo?.id
}

const reportVisible = ref(false)
const target = ref(null)
const reason = ref('')
const submitting = ref(false)

// 查看全文：只看标题和摘要没法判断是否值得举报
const detailVisible = ref(false)
const detail = ref(null)

function openDetail(item) {
  detail.value = item
  detailVisible.value = true
}

onMounted(async () => {
  // 分类与标签用于筛选；两者都是登录即可读取的基础数据
  const [c, t] = await Promise.all([listCategories(), listTags()])
  categories.value = c
  tags.value = t
  await load()
})

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

function resetQuery() {
  query.title = ''
  query.categoryId = null
  query.tagId = null
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
          <el-input v-model="query.title" placeholder="搜索已发布内容" clearable style="width: 200px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="query.categoryId" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="query.tagId" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div v-loading="loading" class="grid">
      <el-empty v-if="!list.length" description="暂无已发布的内容" />
      <el-card v-for="item in list" :key="item.id" shadow="hover" class="item">
        <div class="item-title">
          {{ item.title }}
          <el-tag v-if="isMine(item)" size="small" type="success" effect="plain">我的内容</el-tag>
        </div>
        <div class="item-meta">
          <span>{{ item.authorName }}</span>
          <span>{{ item.categoryName || '未分类' }}</span>
        </div>
        <div class="item-summary">{{ item.summary || item.content?.slice(0, 80) + '...' }}</div>
        <div class="item-footer">
          <span class="time">{{ item.publishTime?.replace('T', ' ').slice(0, 16) }}</span>
          <div>
            <el-button link type="primary" @click="openDetail(item)">查看全文</el-button>
            <el-button v-if="!isMine(item)" link type="danger" @click="openReport(item)">举报</el-button>
          </div>
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

    <!-- 查看全文：内容判定完再决定是否举报 -->
    <el-dialog v-model="detailVisible" :title="detail?.title || '内容详情'" width="720px">
      <template v-if="detail">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="作者">{{ detail.authorName }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ detail.categoryName || '未分类' }}</el-descriptions-item>
          <el-descriptions-item label="发布时间">
            {{ detail.publishTime?.replace('T', ' ').slice(0, 16) }}
          </el-descriptions-item>
        </el-descriptions>
        <div class="content-box">{{ detail.content }}</div>
        <div v-if="detail.tagNames?.length" class="detail-tags">
          标签：<el-tag v-for="t in detail.tagNames" :key="t" size="small" type="info" class="tag">{{ t }}</el-tag>
        </div>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button v-if="detail && !isMine(detail)" type="danger" @click="detailVisible = false; openReport(detail)">
          举报这篇内容
        </el-button>
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

.content-box {
  margin-top: 12px;
  padding: 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.7;
  max-height: 320px;
  overflow: auto;
}

.detail-tags {
  margin-top: 10px;
  color: #6b7280;
  font-size: 13px;
}

.tag {
  margin-right: 4px;
}
</style>

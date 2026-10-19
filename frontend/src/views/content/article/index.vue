<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { offlineArticle, pageArticles } from '@/api/article'
import { listCategories } from '@/api/category'
import { checkText } from '@/api/sensitive'
import { ARTICLE_STATUS, riskText, riskType, statusText, statusType } from '@/utils/articleStatus'

/**
 * 稿件管理（管理员视角）：查看全部稿件、按条件筛选、查看详情、下架已发布稿件。
 * <p>审核动作不在这个页面做 —— 审核员在「审核工作台」处理待审稿件，职责分开。
 */
const loading = ref(false)
const list = ref([])
const total = ref(0)
const categories = ref([])

const query = reactive({ pageNum: 1, pageSize: 10, title: '', status: null, categoryId: null })

const detailVisible = ref(false)
const current = ref(null)
const sensitive = ref(null)
const sensitiveLoading = ref(false)

onMounted(async () => {
  categories.value = await listCategories()
  await load()
})

async function load() {
  loading.value = true
  try {
    const data = await pageArticles(query)
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
  query.status = null
  query.categoryId = null
  query.pageNum = 1
  load()
}

async function openDetail(row) {
  current.value = row
  sensitive.value = null
  detailVisible.value = true
  // 打开详情时顺带跑一次敏感词基线检测，给管理员一个参考
  sensitiveLoading.value = true
  try {
    sensitive.value = await checkText(`${row.title}\n${row.content || ''}`)
  } finally {
    sensitiveLoading.value = false
  }
}

async function onOffline(row) {
  await ElMessageBox.confirm(`确定下架《${row.title}》吗？下架后不再对外展示。`, '提示', { type: 'warning' })
  await offlineArticle(row.id)
  ElMessage.success('已下架')
  detailVisible.value = false
  await load()
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="query.title" placeholder="模糊搜索" clearable style="width: 180px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 130px">
            <el-option v-for="(v, k) in ARTICLE_STATUS" :key="k" :label="v.text" :value="Number(k)" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="query.categoryId" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header><b>稿件列表</b></template>
      <el-table v-loading="loading" :data="list" border>
        <!-- 显示"当前页第几条"，而不是数据库主键：主键会因为测试期间的增删而不连续，
             直接展示 id 看起来像是"序号错乱"。id 只在操作时使用，界面不需要暴露。 -->
        <el-table-column label="序号" width="70">
          <template #default="scope">
            {{ (query.pageNum - 1) * query.pageSize + scope.$index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="authorName" label="作者" width="110" />
        <el-table-column prop="categoryName" label="分类" width="110" />
        <el-table-column label="标签" width="150">
          <template #default="{ row }">
            <el-tag v-for="t in row.tagNames" :key="t" size="small" type="info" class="tag">{{ t }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险" width="90">
          <template #default="{ row }">
            <el-tag :type="riskType(row.riskLevel)" size="small" effect="plain">{{ riskText(row.riskLevel) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
            <el-button
              v-if="row.status === 2"
              v-perm="'article:edit'"
              link
              type="danger"
              @click="onOffline(row)"
            >
              下架
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.pageNum"
        v-model:page-size="query.pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @size-change="load"
        @current-change="load"
      />
    </el-card>

    <el-dialog v-model="detailVisible" :title="current?.title || '稿件详情'" width="760px">
      <template v-if="current">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="作者">{{ current.authorName }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ current.categoryName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(current.status)" size="small">{{ statusText(current.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="riskType(current.riskLevel)" size="small">{{ riskText(current.riskLevel) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="标签" :span="2">
            <el-tag v-for="t in current.tagNames" :key="t" size="small" type="info" class="tag">{{ t }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="content-box">{{ current.content }}</div>

        <el-alert v-if="current.rejectReason" type="warning" :closable="false" class="block">
          <template #title>驳回/阻断原因：{{ current.rejectReason }}</template>
        </el-alert>

        <el-card shadow="never" class="block">
          <template #header>
            <b>敏感词检测（关键词基线）</b>
          </template>
          <div v-loading="sensitiveLoading">
            <template v-if="sensitive">
              <div class="check-line">
                结论：<el-tag :type="sensitive.passed ? 'success' : 'danger'" size="small">
                  {{ sensitive.passed ? '未命中' : '命中' }}
                </el-tag>
                <span class="check-msg">{{ sensitive.message }}</span>
              </div>
              <div v-if="!sensitive.passed" class="check-line">
                命中词：
                <el-tag v-for="w in sensitive.matched" :key="w" type="danger" size="small" class="tag">{{ w }}</el-tag>
              </div>
              <div class="hint">关键词匹配只看"有没有这个词"，看不懂语境（例如作品名可能被误判）。</div>
            </template>
          </div>
        </el-card>
      </template>

      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button
          v-if="current?.status === 2"
          v-perm="'article:edit'"
          type="danger"
          @click="onOffline(current)"
        >
          下架该稿件
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-card {
  margin-top: 16px;
}

.tag {
  margin-right: 4px;
}

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.content-box {
  margin-top: 12px;
  padding: 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.7;
  max-height: 260px;
  overflow: auto;
}

.block {
  margin-top: 12px;
}

.check-line {
  margin-bottom: 8px;
}

.check-msg {
  color: #4b5563;
  margin-left: 6px;
}

.hint {
  color: #9ca3af;
  font-size: 12px;
}
</style>

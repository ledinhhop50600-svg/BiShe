<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { handleReport, pageReports } from '@/api/report'

/**
 * 举报处理（管理员/审核员）：处理创作者对已发布稿件的举报。
 * <p>举报成立时，后端会自动把被举报稿件改为"已下架" —— 这是内容发布后的兜底机制。
 */
const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ pageNum: 1, pageSize: 10, status: null })

const dialogVisible = ref(false)
const current = ref(null)
const form = reactive({ status: 1, remark: '' })
const submitting = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await pageReports(query)
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

function openHandle(row) {
  current.value = row
  form.status = 1
  form.remark = ''
  dialogVisible.value = true
}

async function submit() {
  submitting.value = true
  try {
    await handleReport(current.value.id, form)
    ElMessage.success(form.status === 1 ? '已处理：举报成立，稿件已下架' : '已处理：举报不成立')
    dialogVisible.value = false
    await load()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="处理状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 140px" @change="search">
            <el-option label="待处理" :value="0" />
            <el-option label="举报成立" :value="1" />
            <el-option label="举报不成立" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header><b>举报列表</b></template>
      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="articleTitle" label="被举报稿件" min-width="220" show-overflow-tooltip />
        <el-table-column prop="reporterName" label="举报人" width="110" />
        <el-table-column prop="reason" label="举报理由" min-width="240" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.status === 0" type="warning" size="small">待处理</el-tag>
            <el-tag v-else-if="row.status === 1" type="danger" size="small">成立</el-tag>
            <el-tag v-else type="info" size="small">不成立</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="handlerName" label="处理人" width="110" />
        <el-table-column prop="handleTime" label="处理时间" width="170" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 0" v-perm="'report:handle'" link type="primary" @click="openHandle(row)">处理</el-button>
            <el-button v-else link type="info" disabled>已处理</el-button>
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

    <el-dialog v-model="dialogVisible" title="处理举报" width="560px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="被举报稿件">{{ current?.articleTitle }}</el-descriptions-item>
        <el-descriptions-item label="举报人">{{ current?.reporterName }}</el-descriptions-item>
        <el-descriptions-item label="举报理由">{{ current?.reason }}</el-descriptions-item>
      </el-descriptions>

      <el-form label-width="90px" class="block">
        <el-form-item label="处理结果">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">举报成立（下架稿件）</el-radio>
            <el-radio :value="2">举报不成立</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处理意见">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="说明处理依据，便于后续追溯" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">提交处理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-card {
  margin-top: 16px;
}

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.block {
  margin-top: 16px;
}
</style>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { checkText, createWord, deleteWord, pageWords, updateWord } from '@/api/sensitive'

/**
 * 敏感词库（管理员）。
 * <p>除了维护词条，页面下方提供一个"测试检测"输入框 —— 可以直接体验关键词基线的效果与局限：
 * 它能告诉你"命中了哪个词"，但说不出语境、理由和修改方法。
 */
const CATEGORIES = ['广告法', '虚假宣传', '低俗擦边', '引流诱导', '违禁品', '侵权']

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ pageNum: 1, pageSize: 10, word: '', category: null })

const dialogVisible = ref(false)
const formRef = ref()
const form = reactive({ id: null, word: '', category: '广告法', level: 2, enabled: 1 })
const rules = {
  word: [{ required: true, message: '请输入敏感词', trigger: 'blur' }],
  category: [{ required: true, message: '请选择类别', trigger: 'change' }],
}

const testText = ref('全网最低价的美肤面膜，三天见效不是梦，需要的姐妹加我微信领取清单。')
const testResult = ref(null)
const testing = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await pageWords(query)
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

function openForm(row) {
  Object.assign(form, row ? { ...row } : { id: null, word: '', category: '广告法', level: 2, enabled: 1 })
  dialogVisible.value = true
}

async function submit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (form.id) {
    await updateWord(form)
    ElMessage.success('修改成功')
  } else {
    await createWord(form)
    ElMessage.success('新增成功')
  }
  dialogVisible.value = false
  await load()
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除敏感词「${row.word}」吗？`, '提示', { type: 'warning' })
  await deleteWord(row.id)
  ElMessage.success('删除成功')
  await load()
}

async function runTest() {
  testing.value = true
  try {
    testResult.value = await checkText(testText.value)
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="敏感词">
          <el-input v-model="query.word" placeholder="模糊搜索" clearable style="width: 160px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="类别">
          <el-select v-model="query.category" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <b>敏感词列表（共 {{ total }} 个）</b>
          <el-button v-perm="'audit:sensitive'" type="primary" size="small" @click="openForm(null)">新增敏感词</el-button>
        </div>
      </template>
      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="word" label="敏感词" width="180" />
        <el-table-column prop="category" label="类别" width="120" />
        <el-table-column label="等级" width="110">
          <template #default="{ row }">
            <el-tag :type="row.level >= 3 ? 'danger' : row.level === 2 ? 'warning' : 'info'" size="small">
              {{ row.level === 3 ? '严重' : row.level === 2 ? '违规' : '疑似' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled === 1 ? 'success' : 'info'" size="small">{{ row.enabled === 1 ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button v-perm="'audit:sensitive'" link type="primary" @click="openForm(row)">编辑</el-button>
            <el-button v-perm="'audit:sensitive'" link type="danger" @click="remove(row)">删除</el-button>
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

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <b>检测工具（关键词基线）</b>
          <el-button size="small" :loading="testing" @click="runTest">检测这段文字</el-button>
        </div>
      </template>
      <el-input v-model="testText" type="textarea" :rows="4" placeholder="粘贴一段文字，看关键词匹配会命中什么" />
      <div v-if="testResult" class="result">
        <div class="line">
          结论：
          <el-tag :type="testResult.passed ? 'success' : 'danger'" size="small">
            {{ testResult.passed ? '未命中' : '命中' }}
          </el-tag>
          <span class="msg">{{ testResult.message }}</span>
        </div>
        <div v-if="!testResult.passed" class="line">
          命中词：
          <el-tag v-for="w in testResult.matched" :key="w" type="danger" size="small" class="tag">{{ w }}</el-tag>
        </div>
        <el-alert type="info" :closable="false" class="block">
          <template #title>
            试试把"全网最低价"换成影片名《最好的我们》—— 关键词匹配同样会命中"最"，但它显然不违规。
            这就是后续要用智能体做语义判断的原因，也是论文对比实验的起点。
          </template>
        </el-alert>
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑敏感词' : '新增敏感词'" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="敏感词" prop="word">
          <el-input v-model="form.word" />
        </el-form-item>
        <el-form-item label="类别" prop="category">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级">
          <el-radio-group v-model="form.level">
            <el-radio :value="1">疑似</el-radio>
            <el-radio :value="2">违规</el-radio>
            <el-radio :value="3">严重</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-card {
  margin-top: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.result {
  margin-top: 12px;
}

.line {
  margin-bottom: 8px;
}

.msg {
  color: #4b5563;
  margin-left: 6px;
}

.tag {
  margin-right: 4px;
}

.block {
  margin-top: 10px;
}
</style>

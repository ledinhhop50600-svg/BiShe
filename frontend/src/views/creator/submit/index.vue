<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createArticle, getArticle, submitArticle, updateArticle } from '@/api/article'
import { listCategories, listTags } from '@/api/category'
import { checkText } from '@/api/sensitive'

/**
 * 投稿页（创作者）：写稿、存草稿、发布前检查、提交审核。
 * <p>"发布前检查"目前是**敏感词基线**（关键词匹配）；
 * 阶段 6 会把它升级成智能体的发布前预检 —— 按目标平台规则给出风险提示与具体修改建议。
 */
const route = useRoute()
const router = useRouter()

const categories = ref([])
const tags = ref([])
const formRef = ref()
const saving = ref(false)
const checking = ref(false)
const sensitive = ref(null)

const form = reactive({
  id: null,
  title: '',
  categoryId: null,
  tagIds: [],
  summary: '',
  content: '',
})

const rules = {
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    { max: 200, message: '标题最长 200 个字符', trigger: 'blur' },
  ],
  content: [{ required: true, message: '请输入正文', trigger: 'blur' }],
}

const isEdit = computed(() => !!form.id)

onMounted(async () => {
  const [c, t] = await Promise.all([listCategories(), listTags()])
  categories.value = c
  tags.value = t
  // 从"我的稿件"点编辑进来时带着 id
  if (route.query.id) {
    const article = await getArticle(Number(route.query.id))
    Object.assign(form, {
      id: article.id,
      title: article.title,
      categoryId: article.categoryId,
      tagIds: article.tagIds || [],
      summary: article.summary || '',
      content: article.content,
    })
  }
})

/** 校验并保存（新建或更新），返回稿件 id；校验不通过返回 null */
async function persist() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return null
  }
  saving.value = true
  try {
    if (form.id) {
      await updateArticle(form)
      return form.id
    }
    const id = await createArticle(form)
    form.id = id
    return id
  } finally {
    saving.value = false
  }
}

async function saveDraft() {
  const id = await persist()
  if (!id) {
    return
  }
  ElMessage.success('已保存草稿')
  router.push('/creator/article')
}

async function submitForReview() {
  const id = await persist()
  if (!id) {
    return
  }
  await submitArticle(id)
  ElMessage.success('已提交，等待审核')
  router.push('/creator/article')
}

async function runCheck() {
  if (!form.title && !form.content) {
    ElMessage.warning('请先填写标题或正文')
    return
  }
  checking.value = true
  try {
    sensitive.value = await checkText(`${form.title}\n${form.content}`)
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <b>{{ isEdit ? '编辑稿件' : '写稿投稿' }}</b>
          <span class="hint">保存后为草稿；提交审核后由审核员处理</span>
        </div>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="一句话说清这篇内容" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类">
              <el-select v-model="form.categoryId" placeholder="请选择" clearable style="width: 100%">
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标签">
              <el-select v-model="form.tagIds" multiple placeholder="可多选" style="width: 100%">
                <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="摘要">
          <el-input v-model="form.summary" maxlength="500" show-word-limit placeholder="选填，列表页展示用" />
        </el-form-item>
        <el-form-item label="正文" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="14" placeholder="正文内容" />
        </el-form-item>

        <el-form-item>
          <el-button @click="saveDraft" :loading="saving">保存草稿</el-button>
          <el-button @click="runCheck" :loading="checking">发布前检查</el-button>
          <el-button type="primary" @click="submitForReview" :loading="saving">提交审核</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="sensitive" shadow="never" class="block">
      <template #header>
        <b>发布前检查结果</b>
        <span class="hint">当前为敏感词基线，后续会升级为智能体检查</span>
      </template>
      <div class="line">
        结论：
        <el-tag :type="sensitive.passed ? 'success' : 'warning'" size="small">
          {{ sensitive.passed ? '未命中敏感词' : '命中敏感词' }}
        </el-tag>
        <span class="msg">{{ sensitive.message }}</span>
      </div>
      <div v-if="!sensitive.passed" class="line">
        命中词：
        <el-tag v-for="w in sensitive.matched" :key="w" type="danger" size="small" class="tag">{{ w }}</el-tag>
      </div>
      <el-alert type="info" :closable="false" class="block">
        <template #title>
          关键词匹配只能告诉你"有哪个词"，说不出"为什么违规、该怎么改"。智能体上线后会给出分级判定、判定理由与具体修改建议。
        </template>
      </el-alert>
    </el-card>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hint {
  color: #9ca3af;
  font-size: 12px;
  margin-left: 8px;
}

.block {
  margin-top: 16px;
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
</style>

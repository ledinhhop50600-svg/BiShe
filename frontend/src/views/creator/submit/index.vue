<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createArticle, getArticle, precheckArticle, submitArticle, updateArticle } from '@/api/article'
import { listCategories, listTags } from '@/api/category'
import { riskText, riskType } from '@/utils/articleStatus'

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
const precheck = ref(null)
const articleStatus = ref(null)

const form = reactive({
  id: null,
  title: '',
  categoryId: null,
  tagIds: [],
  summary: '',
  coverImage: '',
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

/** 已发布(2)/已下架(5)：编辑即改后重审（D3 方案 B），保存后直接回到待审核 */
const isResubmit = computed(() => articleStatus.value === 2 || articleStatus.value === 5)

const headerTitle = computed(() => {
  if (isResubmit.value) return '编辑并重新送审'
  return isEdit.value ? '编辑稿件' : '写稿投稿'
})

const headerHint = computed(() => {
  if (isResubmit.value) return '保存后进入待审核，审核通过前内容不再对外展示'
  return '保存后为草稿；提交审核后由审核员处理'
})

onMounted(async () => {
  const [c, t] = await Promise.all([listCategories(), listTags()])
  categories.value = c
  tags.value = t
  // 从"我的稿件"点编辑进来时带着 id
  if (route.query.id) {
    const article = await getArticle(Number(route.query.id))
    articleStatus.value = article.status
    Object.assign(form, {
      id: article.id,
      title: article.title,
      categoryId: article.categoryId,
      tagIds: article.tagIds || [],
      summary: article.summary || '',
      coverImage: article.coverImage || '',
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

/**
 * 已发布/已下架稿件的保存动作：后端 update 会直接把状态改成待审核（D3 方案 B），
 * 所以这里只需要保存，不要再调 /submit（那时状态已经是待审核了）。
 */
async function saveAndResubmit() {
  const id = await persist()
  if (!id) {
    return
  }
  ElMessage.success('已保存并提交审核')
  router.push('/creator/article')
}

async function runCheck() {
  if (!form.title && !form.content) {
    ElMessage.warning('请先填写标题或正文')
    return
  }
  checking.value = true
  try {
    // 智能体预检：不要求先保存，也不落库；与正式审核共用同一套规则
    precheck.value = await precheckArticle(form.title, form.content)
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
          <b>{{ headerTitle }}</b>
          <span class="hint">{{ headerHint }}</span>
        </div>
      </template>

      <el-alert v-if="isResubmit" type="warning" :closable="false" class="block">
        <template #title>
          该稿件当前已{{ articleStatus === 2 ? '发布' : '下架' }}。保存后将进入待审核，
          审核通过前不再对外展示；审核员会基于修改后的内容重新初审。
        </template>
      </el-alert>

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
        <el-form-item label="封面">
          <div class="cover-row">
            <el-input v-model="form.coverImage" maxlength="255" show-word-limit placeholder="选填：封面图片 URL（不填则显示默认封面）" />
            <img v-if="form.coverImage" :src="form.coverImage" class="cover-preview" alt="封面预览" />
          </div>
        </el-form-item>
        <el-form-item label="正文" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="14" placeholder="正文内容" />
        </el-form-item>

        <el-form-item>
          <template v-if="isResubmit">
            <el-button @click="runCheck" :loading="checking">发布前检查</el-button>
            <el-button type="primary" @click="saveAndResubmit" :loading="saving">保存并提交审核</el-button>
          </template>
          <template v-else>
            <el-button @click="saveDraft" :loading="saving">保存草稿</el-button>
            <el-button @click="runCheck" :loading="checking">发布前检查</el-button>
            <el-button type="primary" @click="submitForReview" :loading="saving">提交审核</el-button>
          </template>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="precheck" shadow="never" class="block">
      <template #header>
        <div class="card-header">
          <b>发布前预检（智能体）</b>
          <span class="hint">仅提示，不阻断发布；结论不落库</span>
        </div>
      </template>

      <template v-if="precheck.agentFailed">
        <el-alert type="warning" :closable="false">
          <template #title>{{ precheck.message || '智能体服务不可用，请稍后重试或直接提交人工审核' }}</template>
        </el-alert>
      </template>

      <template v-else>
        <div class="line">
          结论：
          <el-tag :type="riskType(precheck.riskLevel)" size="small">{{ riskText(precheck.riskLevel) }}</el-tag>
          <span class="msg">{{ precheck.reason }}</span>
        </div>
        <div v-if="precheck.hitRules?.length" class="line">
          命中规则：
          <el-tag v-for="r in precheck.hitRules" :key="r.code" type="warning" size="small" class="tag">
            {{ r.code }}
          </el-tag>
        </div>
        <div v-for="(v, idx) in precheck.violations" :key="idx" class="violation">
          <el-tag type="danger" size="small">{{ v.issue }}</el-tag>
          <span class="fragment">「{{ v.fragment }}」</span>
          <div class="suggestion">修改建议：{{ v.suggestion }}</div>
        </div>
        <div v-if="precheck.suggestion" class="suggestion">处置建议：{{ precheck.suggestion }}</div>
        <el-alert type="info" :closable="false" class="block">
          <template #title>
            预检只用于修改参考；正式结论以提交后审核员的初审 + 终审为准。
          </template>
        </el-alert>
      </template>
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

.cover-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.cover-preview {
  width: 88px;
  height: 56px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--app-line);
  background: #f6f1e8;
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

.violation {
  margin-top: 10px;
  padding: 8px 10px;
  background: #fef2f2;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.7;
}

.fragment {
  color: #b91c1c;
  margin-left: 6px;
}

.suggestion {
  color: #6b7280;
  font-size: 12px;
  margin-top: 4px;
  line-height: 1.7;
}
</style>

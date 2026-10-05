<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const band = ref(null)
const error = ref('')
const saved = ref('')
const busy = ref(false)
const form = reactive({
  lowerPct: '',
  upperPct: '',
})

function fillForm(data) {
  form.lowerPct = data ? Number(data.lowerPct) : ''
  form.upperPct = data ? Number(data.upperPct) : ''
}

async function load() {
  error.value = ''
  try {
    const { data } = await api.get('/resin-band/')
    band.value = data || null
    fillForm(band.value)
  } catch {
    error.value = '树脂带加载失败'
  }
}

async function save() {
  error.value = ''
  saved.value = ''
  busy.value = true
  try {
    const { data } = await api.put('/resin-band/', {
      lowerPct: form.lowerPct,
      upperPct: form.upperPct,
    })
    band.value = data
    fillForm(data)
    saved.value = '已保存：晾晒架浸渍流水与浸渍台账即刻按此树脂带过滤。'
  } catch (e) {
    const d = e.response?.data
    error.value =
      d?.lowerPct?.[0] ||
      d?.upperPct?.[0] ||
      d?.detail ||
      (d && typeof d === 'object' ? JSON.stringify(d) : '') ||
      '保存失败'
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <h1>树脂带过滤</h1>
    <p class="sub">
      设定浸渍记录的树脂百分比显示区间（含端点）。保存后，晾晒架下方浸渍流水与浸渍台账只显示落在带内的记录；带外记录不混入，树脂值本身不被改动。
    </p>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="saved" class="ok">{{ saved }}</p>

    <section class="panel">
      <h2 class="feed-title">当前树脂带</h2>
      <p v-if="band" class="band-now">
        <strong>{{ band.lowerPct }}% ~ {{ band.upperPct }}%</strong>
        <span class="hint">
          · 最近由 {{ band.updatedBy || '—' }} 更新于
          {{ band.updatedAt ? new Date(band.updatedAt).toLocaleString() : '—' }}
        </span>
      </p>
      <p v-else class="hint" style="margin:0">尚未设置树脂带：浸渍流水与台账当前显示全部记录。</p>
    </section>

    <form v-if="isAdmin" class="panel row" @submit.prevent="save">
      <label>显示下限 %
        <input
          v-model.number="form.lowerPct"
          type="number"
          step="0.01"
          min="0"
          max="100"
          required
        />
      </label>
      <label>显示上限 %
        <input
          v-model.number="form.upperPct"
          type="number"
          step="0.01"
          min="0"
          max="100"
          required
        />
      </label>
      <button class="btn" type="submit" :disabled="busy">
        {{ busy ? '保存中…' : '保存树脂带' }}
      </button>
    </form>
    <p v-else class="hint">仅管理员可调整树脂带；当前账号为只读。</p>
  </div>
</template>

<style scoped>
.band-now {
  margin: 8px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  align-items: baseline;
  color: var(--navy);
  font-size: 1.05rem;
}
</style>

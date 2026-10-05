<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const band = ref(null)
const form = reactive({ lowerPct: '', upperPct: '' })
const error = ref('')
const notice = ref('')
const busy = ref(false)

function fillForm() {
  if (band.value) {
    form.lowerPct = band.value.lowerPct
    form.upperPct = band.value.upperPct
  }
}

async function load() {
  error.value = ''
  try {
    const { data } = await api.get('/resin-band/')
    band.value = data.band
    fillForm()
  } catch {
    error.value = '树脂带加载失败'
  }
}

async function save() {
  error.value = ''
  notice.value = ''
  busy.value = true
  try {
    const { data } = await api.put('/resin-band/', {
      lowerPct: form.lowerPct,
      upperPct: form.upperPct,
    })
    band.value = data.band
    fillForm()
    notice.value = '已保存：晾晒架浸渍流水与浸渍台账即刻按此树脂带过滤。'
  } catch (e) {
    const d = e.response?.data
    error.value =
      d?.lowerPct?.[0] ||
      d?.upperPct?.[0] ||
      d?.detail ||
      (e.response?.status === 403 ? '仅管理员可调整树脂带' : '保存失败')
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
      设定树脂百分比显示下限与上限。保存后，晾晒架下方浸渍流水与浸渍台账只显示带内记录；带外不混入。仅影响显示，不改动任何浸渍记录的树脂值。
    </p>

    <section class="panel">
      <p v-if="band" class="band-current">
        当前树脂带：<strong>{{ band.lowerPct }}% ~ {{ band.upperPct }}%</strong>
        <span class="hint" v-if="band.updatedBy">
          （{{ band.updatedBy }} 更新于 {{ new Date(band.updatedAt).toLocaleString() }}）
        </span>
      </p>
      <p v-else class="hint" style="margin:0">尚未设定树脂带，流水与台账暂显示全部记录。</p>
    </section>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="notice" class="ok">{{ notice }}</p>

    <form v-if="isAdmin" class="panel row" @submit.prevent="save">
      <label>显示下限 %
        <input v-model.number="form.lowerPct" type="number" step="0.01" min="0" max="100" required />
      </label>
      <label>显示上限 %
        <input v-model.number="form.upperPct" type="number" step="0.01" min="0" max="100" required />
      </label>
      <button class="btn" type="submit" :disabled="busy">
        {{ busy ? '保存中…' : '保存树脂带' }}
      </button>
    </form>
    <p v-else class="hint">仅管理员可调整树脂带；当前账号为 {{ auth.user?.username }}。</p>
  </div>
</template>

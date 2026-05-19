<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useHomeworkStore } from '@/stores/homework'
import { useAuthStore } from '@/stores/auth'
import UploadForm from '@/components/UploadForm.vue'
import TaskList from '@/components/TaskList.vue'

const homework = useHomeworkStore()
const auth = useAuthStore()
const polling = ref<ReturnType<typeof setInterval> | null>(null)

onMounted(() => {
  polling.value = setInterval(() => {
    homework.tasks
      .filter((t) => !['SUCCESS', 'FAILED'].includes(t.status))
      .forEach((t) => homework.pollStatus(t.task_id))
  }, 3000)
})

onUnmounted(() => {
  if (polling.value) clearInterval(polling.value)
})

async function handleUpload(file: File, subject: string, grade: string) {
  if (!auth.user) return
  await homework.upload(file, subject, grade, auth.user.id)
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>作业批改</h1>
      <p>上传作业图片，AI 自动识别并批改</p>
    </div>

    <UploadForm @upload="handleUpload" />

    <div style="margin-top:24px;">
      <TaskList :tasks="homework.tasks" />
    </div>
  </div>
</template>

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { homeworkApi, type TaskStatusResponse, type GradingResultResponse } from '@/api/homework'

export interface TaskItem {
  task_id: string
  status: string
  subject: string
  grade: string
  created_at: string
}

export const useHomeworkStore = defineStore('homework', () => {
  const tasks = ref<TaskItem[]>([])
  const currentResult = ref<GradingResultResponse | null>(null)
  const loading = ref(false)
  const error = ref('')

  async function fetchTasks(userId: number) {
    error.value = ''
    try {
      const { data } = await homeworkApi.getTaskList(userId)
      tasks.value = data.data
    } catch (e) {
      error.value = '获取任务列表失败，请稍后重试'
      console.error(e)
    }
  }
  async function upload(file: File, subject: string, grade: string, userId: number) {
    const form = new FormData()
    form.append('file', file)
    form.append('subject', subject)
    form.append('grade', grade)
    form.append('user_id', String(userId))
    const { data } = await homeworkApi.upload(form)
    const task: TaskItem = {
      task_id: data.data.task_id,
      status: 'PENDING',
      subject,
      grade,
      created_at: new Date().toISOString(),
    }
    tasks.value.unshift(task)
    return data.data.task_id
  }

  async function pollStatus(taskId: string): Promise<TaskStatusResponse> {
    const { data } = await homeworkApi.getStatus(taskId)
    const t = tasks.value.find((x) => x.task_id === taskId)
    if (t) {
      t.status = data.data.status
    }
    return data.data
  }

  async function fetchResult(taskId: string) {
    loading.value = true
    const { data } = await homeworkApi.getResult(taskId)
    currentResult.value = data.data
    loading.value = false
    return data.data
  }

  return { tasks, currentResult, loading, error, upload, pollStatus, fetchResult, fetchTasks }
})

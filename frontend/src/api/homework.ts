import client from './client'

export interface TaskStatusResponse {
  task_id: string
  status: string
  created_at: string
  updated_at: string
}

export interface GradingResult {
  question_no: string
  score: number
  max_score: number
  result: string
  comment?: string
  analysis?: string
  confidence?: number
}

export interface GradingResultResponse {
  task_id: string
  total_score: number
  results: GradingResult[]
  created_at: string
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export const homeworkApi = {
  upload(formData: FormData) {
    return client.post<ApiResponse<{ task_id: string }>>('/homework/upload', formData)
  },
  getStatus(taskId: string) {
    return client.get<ApiResponse<TaskStatusResponse>>(`/homework/status/${taskId}`)
  },
  getResult(taskId: string) {
    return client.get<ApiResponse<GradingResultResponse>>(`/homework/result/${taskId}`)
  },
}

import client from './client'

export interface User {
  id: number
  username: string
  email: string
  full_name?: string
  role: string
  is_active: boolean
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  full_name?: string
  role?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export const authApi = {
  login(data: LoginRequest) {
    return client.post<TokenResponse>('/users/login', data)
  },
  register(data: RegisterRequest) {
    return client.post<User>('/users/register', data)
  },
  getUser(userId: number) {
    return client.get<User>(`/users/${userId}`)
  },
  updateUserStatus(userId: number, isActive: boolean) {
    return client.put<User>(`/users/${userId}/status`, null, {
      params: { is_active: isActive },
    })
  },
}

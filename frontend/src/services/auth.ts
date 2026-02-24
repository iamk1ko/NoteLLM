import http from "@/services/http";
import type { ApiResponse, User } from "@/services/types";

// User Types (Should ideally be in types.ts, but defining here for now if missing)
export type UserProfile = User;

export interface LoginParams {
  username_or_email: string;
  password: string;
}

export interface RegisterParams {
  username: string;
  password: string;
  name: string;
  email?: string;
}

export interface UserUpdateParams {
  name?: string;
  gender?: string;
  phone?: string;
  email?: string;
  bio?: string;
  avatar_file_id?: number;
}

/**
 * Register
 * POST /auth/register
 */
export const register = async (params: RegisterParams): Promise<User> => {
  const { data } = await http.post<ApiResponse<User>>("/auth/register", params);
  return data.data;
};

/**
 * Login
 * POST /auth/login
 */
export const login = async (params: LoginParams): Promise<User> => {
  const { data } = await http.post<ApiResponse<User>>("/auth/login", params);
  return data.data;
};

/**
 * Logout
 * POST /auth/logout
 */
export const logout = async (): Promise<void> => {
  await http.post("/auth/logout");
};

/**
 * Get Current User
 * GET /users/me
 */
export const getCurrentUser = async (): Promise<UserProfile> => {
  const { data } = await http.get<ApiResponse<UserProfile>>("/users/me");
  return data.data;
};

/**
 * Update User Profile
 * PUT /users/{id}
 */
export const updateUser = async (userId: number, params: UserUpdateParams): Promise<User> => {
  const { data } = await http.put<ApiResponse<User>>(`/users/${userId}`, params);
  return data.data;
};

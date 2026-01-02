/**
 * Task API endpoints for async Claude operations.
 * Handles long-running tasks that might outlive the app session.
 */

import { z } from 'zod';
import { api } from '../client';

/**
 * Task status enum
 */
export enum TaskStatus {
	PENDING = 'pending',
	RUNNING = 'running',
	COMPLETED = 'completed',
	FAILED = 'failed'
}

/**
 * Request schema for creating a chat task
 */
export const ChatTaskRequestSchema = z.object({
	message: z.string().min(1, 'Message cannot be empty'),
	session_id: z.string().optional(),
	project_path: z.string().optional(),
	dangerously_skip_permissions: z.boolean().default(false)
});

export type ChatTaskRequest = z.infer<typeof ChatTaskRequestSchema>;

/**
 * Response schema for task creation
 */
export const TaskResponseSchema = z.object({
	task_id: z.string(),
	status: z.nativeEnum(TaskStatus),
	message: z.string()
});

export type TaskResponse = z.infer<typeof TaskResponseSchema>;

/**
 * Task info schema with full details
 */
export const TaskInfoSchema = z.object({
	task_id: z.string(),
	status: z.nativeEnum(TaskStatus),
	message: z.string(),
	session_id: z.string().nullable(),
	project_path: z.string().nullable(),
	result: z.string().nullable(),
	error: z.string().nullable(),
	exit_code: z.number().nullable(),
	stderr: z.string().nullable(),
	created_at: z.string(),
	updated_at: z.string(),
	expires_at: z.string()
});

export type TaskInfo = z.infer<typeof TaskInfoSchema>;

const BASE_ENDPOINT = '/api/v1';

/**
 * Create a new chat task
 */
export async function createChatTask(request: ChatTaskRequest): Promise<TaskResponse> {
	const validatedRequest = ChatTaskRequestSchema.parse(request);

	return api.postWithValidation(`${BASE_ENDPOINT}/tasks/chat`, TaskResponseSchema, validatedRequest, {
		timeout: 5000 // Quick timeout since this just creates the task
	});
}

/**
 * Get task status and results
 */
export async function getTaskStatus(taskId: string): Promise<TaskInfo> {
	return api.getWithValidation(`${BASE_ENDPOINT}/tasks/${taskId}`, TaskInfoSchema, {
		timeout: 5000
	});
}

/**
 * List all tasks (for debugging)
 */
export async function listTasks(): Promise<TaskInfo[]> {
	return api.getWithValidation(`${BASE_ENDPOINT}/tasks`, z.array(TaskInfoSchema), {
		timeout: 10000
	});
}

/**
 * Poll for task completion
 *
 * @param taskId - Task ID to poll
 * @param options - Polling options
 * @returns Promise that resolves when task completes
 */
export async function pollForCompletion(
	taskId: string,
	options: {
		intervalMs?: number;
		maxAttempts?: number;
		onProgress?: (task: TaskInfo) => void;
	} = {}
): Promise<TaskInfo> {
	const { intervalMs = 2000, maxAttempts = 150, onProgress } = options; // 5 minutes max

	let attempts = 0;

	while (attempts < maxAttempts) {
		const task = await getTaskStatus(taskId);

		// Call progress callback if provided
		if (onProgress) {
			onProgress(task);
		}

		// Check if task is in a terminal state
		if (task.status === TaskStatus.COMPLETED || task.status === TaskStatus.FAILED) {
			return task;
		}

		// Wait before next poll
		await new Promise((resolve) => setTimeout(resolve, intervalMs));
		attempts++;
	}

	throw new Error(`Task polling timeout after ${maxAttempts} attempts`);
}

export const tasks = {
	createChatTask,
	getTaskStatus,
	listTasks,
	pollForCompletion
};

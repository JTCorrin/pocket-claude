/**
 * Claude Code API endpoint module
 *
 * Provides typed functions for interacting with the Claude Code API:
 * - List and filter sessions
 * - Send messages to Claude Code CLI
 * - Check Claude CLI health status
 * - List projects
 */

import { z } from 'zod';
import { api } from '../client';
import { dateStringSchema } from '../schemas';

// ============================================================================
// Schemas
// ============================================================================

/**
 * Session information schema
 */
export const sessionSchema = z.object({
	session_id: z.string(),
	project: z.string(),
	preview: z.string(),
	last_active: dateStringSchema,
	message_count: z.number().int()
});

export type Session = z.infer<typeof sessionSchema>;

/**
 * Sessions list response schema
 */
export const sessionsResponseSchema = z.object({
	sessions: z.array(sessionSchema)
});

export type SessionsResponse = z.infer<typeof sessionsResponseSchema>;

/**
 * Chat request schema
 */
export const chatRequestSchema = z.object({
	message: z.string().min(1),
	session_id: z.string().optional(),
	project_path: z.string().optional(),
	dangerously_skip_permissions: z.boolean().optional().default(false)
});

export type ChatRequest = z.infer<typeof chatRequestSchema>;

/**
 * Chat response schema
 */
export const chatResponseSchema = z.object({
	response: z.string(),
	session_id: z.string(),
	exit_code: z.number().int(),
	stderr: z.string()
});

export type ChatResponse = z.infer<typeof chatResponseSchema>;

/**
 * Health check response schema
 */
export const healthResponseSchema = z.object({
	status: z.string(),
	claude_version: z.string(),
	api_key_configured: z.boolean()
});

export type HealthResponse = z.infer<typeof healthResponseSchema>;

/**
 * Project information schema
 */
export const projectSchema = z.object({
	path: z.string(),
	session_count: z.number().int(),
	last_active: dateStringSchema
});

export type Project = z.infer<typeof projectSchema>;

/**
 * Projects list response schema
 */
export const projectsResponseSchema = z.object({
	projects: z.array(projectSchema)
});

export type ProjectsResponse = z.infer<typeof projectsResponseSchema>;

// ============================================================================
// API Functions
// ============================================================================

const BASE_ENDPOINT = '/api/v1';

/**
 * List available Claude Code sessions
 *
 * @param params - Optional query parameters
 * @param params.limit - Maximum number of sessions to return (1-100, default 20)
 * @param params.project - Filter by project path
 *
 * @example
 * ```typescript
 * const { sessions } = await claude.listSessions({ limit: 10 });
 * ```
 */
export async function listSessions(params?: { limit?: number; project?: string }) {
	const queryParams = new URLSearchParams();
	if (params?.limit) queryParams.set('limit', String(params.limit));
	if (params?.project) queryParams.set('project', params.project);

	const query = queryParams.toString();
	const url = query ? `${BASE_ENDPOINT}/sessions?${query}` : `${BASE_ENDPOINT}/sessions`;

	return api.getWithValidation(url, sessionsResponseSchema);
}

/**
 * Send a message to Claude Code
 *
 * @param request - Chat request parameters
 * @param request.message - The message to send
 * @param request.session_id - Optional session ID to resume
 * @param request.project_path - Optional project path
 * @param request.dangerously_skip_permissions - Skip permission prompts (use with caution)
 *
 * @example
 * ```typescript
 * // New conversation
 * const result = await claude.chat({
 *   message: 'Explain this codebase'
 * });
 *
 * // Resume existing session
 * const result = await claude.chat({
 *   message: 'What files handle routing?',
 *   session_id: 'abc-123-def'
 * });
 * ```
 */
export async function chat(request: ChatRequest) {
	// Validate input before sending
	const validatedRequest = chatRequestSchema.parse(request);

	return api.postWithValidation(`${BASE_ENDPOINT}/chat`, chatResponseSchema, validatedRequest);
}

/**
 * Check Claude CLI health status
 *
 * @example
 * ```typescript
 * const health = await claude.health();
 * if (health.status === 'ok') {
 *   console.log(`Claude version: ${health.claude_version}`);
 * }
 * ```
 */
export async function health() {
	return api.getWithValidation(`${BASE_ENDPOINT}/health`, healthResponseSchema);
}

/**
 * List known Claude Code projects
 *
 * @example
 * ```typescript
 * const { projects } = await claude.listProjects();
 * ```
 */
export async function listProjects() {
	return api.getWithValidation(`${BASE_ENDPOINT}/projects`, projectsResponseSchema);
}

// ============================================================================
// Export as namespace-like object
// ============================================================================

/**
 * Claude Code API endpoint module
 *
 * Usage:
 * ```typescript
 * import { claude } from '$lib/api';
 *
 * // In a component
 * <script lang="ts">
 *   import { claude } from '$lib/api';
 *
 *   let sessions = $state<Session[]>([]);
 *
 *   onMount(async () => {
 *     const result = await claude.listSessions({ limit: 20 });
 *     sessions = result.sessions;
 *   });
 *
 *   async function sendMessage(message: string) {
 *     const result = await claude.chat({ message });
 *     console.log(result.response);
 *   }
 * </script>
 * ```
 */
export const claude = {
	// Schemas (for external validation if needed)
	schemas: {
		session: sessionSchema,
		sessionsResponse: sessionsResponseSchema,
		chatRequest: chatRequestSchema,
		chatResponse: chatResponseSchema,
		healthResponse: healthResponseSchema,
		project: projectSchema,
		projectsResponse: projectsResponseSchema
	},
	// API methods
	listSessions,
	chat,
	health,
	listProjects
};

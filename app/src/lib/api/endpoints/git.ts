/**
 * Git provider settings API endpoints.
 * Handles OAuth flows and git connections.
 */

import { z } from 'zod';
import { api, del } from '../client';

const BASE_ENDPOINT = '/api/v1/git';

/**
 * Git provider enum
 */
export enum GitProvider {
	GITHUB = 'github',
	GITLAB = 'gitlab',
	GITEA = 'gitea'
}

/**
 * OAuth initiate request schema
 */
export const OAuthInitiateRequestSchema = z.object({
	provider: z.nativeEnum(GitProvider),
	instance_url: z.string().url().optional(),
	code_challenge: z.string().min(43).max(128),
	code_challenge_method: z.string().default('S256'),
	redirect_uri: z.string().min(1) // Accept custom URL schemes like pocketclaude://
});

export type OAuthInitiateRequest = z.infer<typeof OAuthInitiateRequestSchema>;

/**
 * OAuth initiate response schema
 */
export const OAuthInitiateResponseSchema = z.object({
	authorization_url: z.string().url(),
	state: z.string()
});

export type OAuthInitiateResponse = z.infer<typeof OAuthInitiateResponseSchema>;

/**
 * OAuth callback request schema
 */
export const OAuthCallbackRequestSchema = z.object({
	provider: z.nativeEnum(GitProvider),
	code: z.string(),
	state: z.string(),
	code_verifier: z.string().min(43).max(128),
	redirect_uri: z.string().min(1) // Accept custom URL schemes like pocketclaude://
});

export type OAuthCallbackRequest = z.infer<typeof OAuthCallbackRequestSchema>;

/**
 * Git connection schema
 */
export const GitConnectionSchema = z.object({
	id: z.string(),
	provider: z.nativeEnum(GitProvider),
	instance_url: z.string().url().nullable(),
	username: z.string().nullable(),
	email: z.string().email().nullable(),
	connected_at: z.string(),
	is_active: z.boolean()
});

export type GitConnection = z.infer<typeof GitConnectionSchema>;

/**
 * Git connection status schema
 */
export const GitConnectionStatusSchema = z.object({
	connection_id: z.string(),
	is_valid: z.boolean(),
	username: z.string().nullable(),
	scopes: z.array(z.string()),
	last_checked: z.string()
});

export type GitConnectionStatus = z.infer<typeof GitConnectionStatusSchema>;

/**
 * Initiate OAuth flow
 */
export async function initiateOAuth(
	request: OAuthInitiateRequest
): Promise<OAuthInitiateResponse> {
	return api.postWithValidation(
		`${BASE_ENDPOINT}/oauth/initiate`,
		OAuthInitiateResponseSchema,
		request
	);
}

/**
 * Handle OAuth callback
 */
export async function handleOAuthCallback(
	request: OAuthCallbackRequest
): Promise<GitConnection> {
	return api.postWithValidation(
		`${BASE_ENDPOINT}/oauth/callback`,
		GitConnectionSchema,
		request
	);
}

/**
 * List git connections
 */
export async function listConnections(): Promise<GitConnection[]> {
	return api.getWithValidation(`${BASE_ENDPOINT}/connections`, z.array(GitConnectionSchema));
}

/**
 * Get a specific git connection
 */
export async function getConnection(connectionId: string): Promise<GitConnection> {
	return api.getWithValidation(`${BASE_ENDPOINT}/connections/${connectionId}`, GitConnectionSchema);
}

/**
 * Delete a git connection
 */
export async function deleteConnection(connectionId: string): Promise<void> {
	await del(`${BASE_ENDPOINT}/connections/${connectionId}`);
}

/**
 * Check connection status
 */
export async function checkConnectionStatus(connectionId: string): Promise<GitConnectionStatus> {
	return api.getWithValidation(
		`${BASE_ENDPOINT}/connections/${connectionId}/status`,
		GitConnectionStatusSchema
	);
}

/**
 * Generate PKCE code verifier and challenge
 */
export function generatePKCE(): { codeVerifier: string; codeChallenge: string } {
	// Generate random code verifier (43-128 chars)
	const array = new Uint8Array(32);
	crypto.getRandomValues(array);
	const codeVerifier = base64URLEncode(array);

	// We'll compute SHA256 in the calling code since crypto.subtle is async
	return {
		codeVerifier,
		codeChallenge: '' // Will be computed asynchronously
	};
}

/**
 * Generate code challenge from code verifier
 */
export async function generateCodeChallenge(codeVerifier: string): Promise<string> {
	const encoder = new TextEncoder();
	const data = encoder.encode(codeVerifier);
	const hash = await crypto.subtle.digest('SHA-256', data);
	return base64URLEncode(new Uint8Array(hash));
}

/**
 * Base64 URL encode (RFC 4648)
 */
function base64URLEncode(buffer: Uint8Array): string {
	const base64 = btoa(String.fromCharCode(...buffer));
	return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

export const git = {
	initiateOAuth,
	handleOAuthCallback,
	listConnections,
	getConnection,
	deleteConnection,
	checkConnectionStatus,
	generatePKCE,
	generateCodeChallenge
};

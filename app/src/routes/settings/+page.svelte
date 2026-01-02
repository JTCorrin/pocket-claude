<script lang="ts">
	import { onMount } from 'svelte';
	import { Browser } from '@capacitor/browser';
	import { App } from '@capacitor/app';
	import { apiClient, getApiBaseUrl, setApiBaseUrl, clearApiBaseUrl } from '$lib/api';
	import type { GitConnection } from '$lib/api/endpoints/git';
	import { GitProvider } from '$lib/api/endpoints/git';

	let connections = $state<GitConnection[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	// API URL configuration
	let apiUrl = $state<string>('');
	let editingApiUrl = $state(false);

	// OAuth state storage
	let oauthState = $state<{
		provider: GitProvider;
		codeVerifier: string;
		state: string;
		instanceUrl?: string;
	} | null>(null);
	
	// Modal states
	let showDeleteConfirm = $state(false);
	let connectionToDelete = $state<string | null>(null);
	let showInstanceUrlInput = $state(false);
	let instanceUrlProvider = $state<GitProvider | null>(null);
	let instanceUrlValue = $state('');

	const REDIRECT_URI = 'pocketclaude://oauth-callback';

	onMount(async () => {
		// Load current API URL
		apiUrl = getApiBaseUrl() || '';

		await loadConnections();
		setupDeepLinkListener();
	});

	function saveApiUrl() {
		try {
			// Validate URL
			const url = apiUrl.trim();
			if (!url) {
				error = 'API URL cannot be empty';
				return;
			}

			// Basic URL validation
			try {
				new URL(url);
			} catch {
				error = 'Invalid URL format. Use format: http://localhost:8000 or https://api.example.com';
				return;
			}

			// Remove trailing slash
			const cleanUrl = url.replace(/\/$/, '');

			setApiBaseUrl(cleanUrl);
			apiUrl = cleanUrl;
			editingApiUrl = false;
			successMessage = 'API URL saved successfully';
			error = null;

			// Clear success message after 3 seconds
			setTimeout(() => {
				successMessage = null;
			}, 3000);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save API URL';
		}
	}

	function resetApiUrl() {
		clearApiBaseUrl();
		apiUrl = getApiBaseUrl() || '';
		editingApiUrl = false;
		successMessage = 'API URL reset to default';
		error = null;

		setTimeout(() => {
			successMessage = null;
		}, 3000);
	}

	async function loadConnections() {
		loading = true;
		error = null;

		try {
			connections = await apiClient.git.listConnections();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load connections';
			console.error('Error loading connections:', err);
		} finally {
			loading = false;
		}
	}

	async function connectProvider(provider: GitProvider, instanceUrl?: string) {
		loading = true;
		error = null;

		try {
			// Generate PKCE parameters
			const { codeVerifier } = apiClient.git.generatePKCE();
			const codeChallenge = await apiClient.git.generateCodeChallenge(codeVerifier);

			// Initiate OAuth flow
			const oauth = await apiClient.git.initiateOAuth({
				provider,
				instance_url: instanceUrl,
				code_challenge: codeChallenge,
				code_challenge_method: 'S256',
				redirect_uri: REDIRECT_URI
			});

			// Store OAuth state for callback
			oauthState = {
				provider,
				codeVerifier,
				state: oauth.state,
				instanceUrl
			};

			// Save to sessionStorage so it is cleared when the session ends
			sessionStorage.setItem('oauth_state', JSON.stringify(oauthState));

			// Open authorization URL in browser
			await Browser.open({
				url: oauth.authorization_url,
				presentationStyle: 'popover'
			});
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to initiate OAuth';
			console.error('OAuth initiation error:', err);
		} finally {
			loading = false;
		}
	}

	function setupDeepLinkListener() {
		// Listen for deep link when returning from OAuth
		App.addListener('appUrlOpen', async (event) => {
			const url = event.url;

			// Check if this is an OAuth callback
			if (url.startsWith(REDIRECT_URI)) {
				await handleOAuthCallback(url);
			}
		});
	}

	async function handleOAuthCallback(url: string) {
		try {
			// Parse URL parameters
			const urlObj = new URL(url);
			const code = urlObj.searchParams.get('code');
			const state = urlObj.searchParams.get('state');

			if (!code || !state) {
				throw new Error('Missing OAuth parameters');
			}

			// Restore OAuth state
			const storedState = sessionStorage.getItem('oauth_state');
			if (!storedState) {
				throw new Error('No OAuth state found');
			}

			oauthState = JSON.parse(storedState);

			if (oauthState?.state !== state) {
				throw new Error('OAuth state mismatch');
			}

			// Exchange code for token
			const connection = await apiClient.git.handleOAuthCallback({
				provider: oauthState.provider,
				code,
				state,
				code_verifier: oauthState.codeVerifier,
				redirect_uri: REDIRECT_URI
			});

			// Clear OAuth state
			sessionStorage.removeItem('oauth_state');
			oauthState = null;

			// Reload connections
			await loadConnections();

			// Close browser
			await Browser.close();
		} catch (err) {
			error = err instanceof Error ? err.message : 'OAuth callback failed';
			console.error('OAuth callback error:', err);
		}
	}

	async function deleteConnection(connectionId: string) {
		connectionToDelete = connectionId;
		showDeleteConfirm = true;
	}
	
	async function confirmDelete() {
		if (!connectionToDelete) return;

		try {
			await apiClient.git.deleteConnection(connectionToDelete);
			await loadConnections();
			successMessage = 'Connection deleted successfully';
			setTimeout(() => {
				successMessage = null;
			}, 3000);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to delete connection';
			console.error('Delete error:', err);
		} finally {
			showDeleteConfirm = false;
			connectionToDelete = null;
		}
	}
	
	function cancelDelete() {
		showDeleteConfirm = false;
		connectionToDelete = null;
	}
	
	function showInstanceUrlModal(provider: GitProvider) {
		instanceUrlProvider = provider;
		instanceUrlValue = provider === GitProvider.GITLAB ? 'https://gitlab.com' : '';
		showInstanceUrlInput = true;
	}
	
	async function submitInstanceUrl() {
		if (!instanceUrlProvider || !instanceUrlValue.trim()) {
			error = 'Instance URL is required';
			return;
		}
		
		showInstanceUrlInput = false;
		await connectProvider(instanceUrlProvider, instanceUrlValue.trim());
		instanceUrlProvider = null;
		instanceUrlValue = '';
	}
	
	function cancelInstanceUrl() {
		showInstanceUrlInput = false;
		instanceUrlProvider = null;
		instanceUrlValue = '';
	}

	function getProviderIcon(provider: GitProvider): string {
		switch (provider) {
			case GitProvider.GITHUB:
				return '🐙';
			case GitProvider.GITLAB:
				return '🦊';
			case GitProvider.GITEA:
				return '🍵';
			default:
				return '📦';
		}
	}

	function getProviderName(provider: GitProvider): string {
		switch (provider) {
			case GitProvider.GITHUB:
				return 'GitHub';
			case GitProvider.GITLAB:
				return 'GitLab';
			case GitProvider.GITEA:
				return 'Gitea';
			default:
				return provider;
		}
	}
</script>

<div class="settings-page">
	<header>
		<h1>Settings</h1>
		<p class="subtitle">Configure your Pocket Claude instance</p>
	</header>

	{#if error}
		<div class="error-banner">
			<span>⚠️</span>
			<span>{error}</span>
			<button onclick={() => (error = null)}>×</button>
		</div>
	{/if}

	{#if successMessage}
		<div class="success-banner">
			<span>✓</span>
			<span>{successMessage}</span>
			<button onclick={() => (successMessage = null)}>×</button>
		</div>
	{/if}

	<section class="api-config-section">
		<h2>API Configuration</h2>
		<p class="section-description">
			Configure the backend API URL for your Pocket Claude server
		</p>

		<div class="api-url-form">
			{#if editingApiUrl}
				<div class="form-group">
					<label for="api-url">API Base URL</label>
					<input
						type="url"
						id="api-url"
						bind:value={apiUrl}
						placeholder="https://api.example.com or http://localhost:8000"
						class="api-url-input"
					/>
					<p class="help-text">
						Enter the full URL of your backend API (without trailing slash)
					</p>
				</div>

				<div class="button-group">
					<button class="btn-primary" onclick={saveApiUrl}>Save</button>
					<button class="btn-secondary" onclick={() => (editingApiUrl = false)}>Cancel</button>
					<button class="btn-danger" onclick={resetApiUrl}>Reset to Default</button>
				</div>
			{:else}
				<div class="api-url-display">
					<div class="url-info">
						<span class="label">Current API URL:</span>
						<code class="url-value">{apiUrl || 'Not configured'}</code>
					</div>
					<button class="btn-secondary" onclick={() => (editingApiUrl = true)}>Edit</button>
				</div>
			{/if}
		</div>
	</section>

	<section class="connections-section">
		<h2>Git Connections</h2>

		{#if connections.length > 0}
			<div class="connections-list">
				{#each connections as connection}
					<div class="connection-card">
						<div class="connection-header">
							<span class="provider-icon">{getProviderIcon(connection.provider)}</span>
							<div class="connection-info">
								<h3>{getProviderName(connection.provider)}</h3>
								{#if connection.username}
									<p class="username">@{connection.username}</p>
								{/if}
								{#if connection.instance_url}
									<p class="instance-url">{connection.instance_url}</p>
								{/if}
							</div>
						</div>

						<div class="connection-actions">
							<span class="status-badge active">Connected</span>
							<button class="btn-danger" onclick={() => deleteConnection(connection.id)}>
								Disconnect
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<div class="add-connection">
			<h3>Add New Connection</h3>
			<div class="provider-buttons">
				<button
					class="provider-btn"
					onclick={() => connectProvider(GitProvider.GITHUB)}
					disabled={loading}
				>
					<span class="provider-icon">🐙</span>
					<span>GitHub</span>
				</button>

				<button
					class="provider-btn"
					onclick={() => showInstanceUrlModal(GitProvider.GITLAB)}
					disabled={loading}
				>
					<span class="provider-icon">🦊</span>
					<span>GitLab</span>
				</button>

				<button
					class="provider-btn"
					onclick={() => showInstanceUrlModal(GitProvider.GITEA)}
					disabled={loading}
				>
					<span class="provider-icon">🍵</span>
					<span>Gitea</span>
				</button>
			</div>
		</div>

		{#if loading}
			<div class="loading">
				<div class="spinner"></div>
				<p>Loading...</p>
			</div>
		{/if}
	</section>
	
	<!-- Delete confirmation modal -->
	{#if showDeleteConfirm}
		<div class="modal-overlay" onclick={cancelDelete}>
			<div class="modal" onclick={(e) => e.stopPropagation()}>
				<h3>Confirm Deletion</h3>
				<p>Are you sure you want to disconnect this git provider?</p>
				<div class="modal-actions">
					<button class="btn-secondary" onclick={cancelDelete}>Cancel</button>
					<button class="btn-danger" onclick={confirmDelete}>Delete</button>
				</div>
			</div>
		</div>
	{/if}
	
	<!-- Instance URL input modal -->
	{#if showInstanceUrlInput}
		<div class="modal-overlay" onclick={cancelInstanceUrl}>
			<div class="modal" onclick={(e) => e.stopPropagation()}>
				<h3>Enter Instance URL</h3>
				<p>
					{#if instanceUrlProvider === GitProvider.GITLAB}
						Enter your GitLab instance URL (e.g., https://gitlab.com):
					{:else if instanceUrlProvider === GitProvider.GITEA}
						Enter your Gitea instance URL:
					{/if}
				</p>
				<input
					type="url"
					bind:value={instanceUrlValue}
					placeholder="https://example.com"
					class="url-input"
					onkeydown={(e) => e.key === 'Enter' && submitInstanceUrl()}
				/>
				<div class="modal-actions">
					<button class="btn-secondary" onclick={cancelInstanceUrl}>Cancel</button>
					<button class="btn-primary" onclick={submitInstanceUrl}>Connect</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.settings-page {
		max-width: 800px;
		margin: 0 auto;
		padding: 2rem 1rem;
	}

	header {
		margin-bottom: 2rem;
	}

	h1 {
		font-size: 2rem;
		font-weight: bold;
		margin-bottom: 0.5rem;
	}

	.subtitle {
		color: #666;
		font-size: 1rem;
	}

	.error-banner {
		background: #fee;
		border: 1px solid #fcc;
		border-radius: 8px;
		padding: 1rem;
		margin-bottom: 1.5rem;
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.error-banner button {
		margin-left: auto;
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: #c00;
	}

	.success-banner {
		background: #d4edda;
		border: 1px solid #c3e6cb;
		border-radius: 8px;
		padding: 1rem;
		margin-bottom: 1.5rem;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		color: #155724;
	}

	.success-banner button {
		margin-left: auto;
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: #155724;
	}

	.api-config-section,
	.connections-section {
		background: white;
		border-radius: 12px;
		padding: 1.5rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		margin-bottom: 1.5rem;
	}

	.section-description {
		color: #666;
		font-size: 0.875rem;
		margin-bottom: 1rem;
	}

	.api-url-form {
		margin-top: 1rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	label {
		font-weight: 600;
		font-size: 0.875rem;
		color: #333;
	}

	.api-url-input {
		padding: 0.75rem;
		border: 1px solid #e0e0e0;
		border-radius: 6px;
		font-size: 0.875rem;
		font-family: 'Monaco', 'Menlo', monospace;
	}

	.api-url-input:focus {
		outline: none;
		border-color: #007bff;
		box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
	}

	.help-text {
		font-size: 0.75rem;
		color: #999;
	}

	.button-group {
		display: flex;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.btn-primary {
		background: #007bff;
		color: white;
		border: none;
		padding: 0.5rem 1.5rem;
		border-radius: 6px;
		cursor: pointer;
		font-weight: 500;
	}

	.btn-primary:hover {
		background: #0056b3;
	}

	.btn-secondary {
		background: #6c757d;
		color: white;
		border: none;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		cursor: pointer;
		font-weight: 500;
	}

	.btn-secondary:hover {
		background: #545b62;
	}

	.api-url-display {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		background: #f8f9fa;
		border-radius: 6px;
	}

	.url-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.url-info .label {
		font-size: 0.75rem;
		color: #666;
		font-weight: 600;
	}

	.url-value {
		font-family: 'Monaco', 'Menlo', monospace;
		font-size: 0.875rem;
		background: white;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		border: 1px solid #e0e0e0;
	}

	h2 {
		font-size: 1.5rem;
		font-weight: 600;
		margin-bottom: 1rem;
	}

	h3 {
		font-size: 1.125rem;
		font-weight: 600;
	}

	.connections-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-bottom: 2rem;
	}

	.connection-card {
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		padding: 1rem;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.connection-header {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.provider-icon {
		font-size: 2rem;
	}

	.connection-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.username {
		color: #666;
		font-size: 0.875rem;
	}

	.instance-url {
		color: #999;
		font-size: 0.75rem;
	}

	.connection-actions {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.status-badge {
		padding: 0.25rem 0.75rem;
		border-radius: 12px;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.status-badge.active {
		background: #d4edda;
		color: #155724;
	}

	.btn-danger {
		background: #dc3545;
		color: white;
		border: none;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		cursor: pointer;
		font-weight: 500;
	}

	.btn-danger:hover {
		background: #c82333;
	}

	.add-connection {
		border-top: 1px solid #e0e0e0;
		padding-top: 1.5rem;
	}

	.provider-buttons {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 1rem;
		margin-top: 1rem;
	}

	.provider-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 1.5rem 1rem;
		border: 2px solid #e0e0e0;
		border-radius: 8px;
		background: white;
		cursor: pointer;
		transition: all 0.2s;
	}

	.provider-btn:hover:not(:disabled) {
		border-color: #007bff;
		background: #f8f9fa;
	}

	.provider-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.loading {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 2rem;
	}

	.spinner {
		width: 40px;
		height: 40px;
		border: 4px solid #f3f3f3;
		border-top: 4px solid #007bff;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}

	@media (max-width: 640px) {
		.connection-card {
			flex-direction: column;
			align-items: flex-start;
			gap: 1rem;
		}

		.connection-actions {
			width: 100%;
			justify-content: space-between;
		}

		.provider-buttons {
			grid-template-columns: 1fr;
		}
	}

	/* Modal styles */
	.modal-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 1rem;
	}

	.modal {
		background: white;
		border-radius: 12px;
		padding: 2rem;
		max-width: 500px;
		width: 100%;
		box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
	}

	.modal h3 {
		margin-bottom: 1rem;
		font-size: 1.25rem;
		font-weight: 600;
	}

	.modal p {
		margin-bottom: 1.5rem;
		color: #666;
		line-height: 1.5;
	}

	.url-input {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #e0e0e0;
		border-radius: 6px;
		font-size: 0.875rem;
		margin-bottom: 1.5rem;
		font-family: 'Monaco', 'Menlo', monospace;
	}

	.url-input:focus {
		outline: none;
		border-color: #007bff;
		box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
	}

	.modal-actions {
		display: flex;
		gap: 0.75rem;
		justify-content: flex-end;
	}

	.btn-danger {
		background: #dc3545;
		color: white;
		border: none;
		padding: 0.5rem 1.5rem;
		border-radius: 6px;
		cursor: pointer;
		font-weight: 500;
	}

	.btn-danger:hover {
		background: #c82333;
	}

</style>

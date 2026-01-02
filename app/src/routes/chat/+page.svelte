<script lang="ts">
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api';
	import type { Session, ChatResponse } from '$lib/api/endpoints/claude';
	import ChatMessage from '$lib/components/chat-message.svelte';
	import SessionSelector from '$lib/components/session-selector.svelte';
	import ChatInput from '$lib/components/chat-input.svelte';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';

	type Message = {
		role: 'user' | 'assistant';
		content: string;
		timestamp: Date;
	};

	// State
	let sessions = $state<Session[]>([]);
	let selectedSession = $state<Session | null>(null);
	let messages = $state<Message[]>([]);
	let loading = $state(false);
	let sendingMessage = $state(false);
	let error = $state<string | null>(null);

	// Refs
	let messagesEndRef = $state<HTMLDivElement>();

	// Load sessions on mount
	onMount(async () => {
		await loadSessions();
	});

	async function loadSessions() {
		loading = true;
		error = null;
		try {
			const result = await apiClient.claude.listSessions({ limit: 20 });
			sessions = result.sessions;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load sessions';
			console.error('Error loading sessions:', err);
		} finally {
			loading = false;
		}
	}

	function handleSelectSession(session: Session | null) {
		selectedSession = session;
		messages = [];

		// If starting a new chat, clear the selected session
		if (session === null) {
			return;
		}

		// TODO: In a full implementation, we would load the session's message history here
		// For now, just show a welcome message
		messages = [
			{
				role: 'assistant',
				content: `Loaded session for project: ${session.project}\n\nLast active: ${new Date(session.last_active).toLocaleString()}\nMessage count: ${session.message_count}`,
				timestamp: new Date()
			}
		];

		scrollToBottom();
	}

	async function handleSendMessage(messageText: string) {
		if (!messageText.trim()) return;

		// Add user message
		const userMessage: Message = {
			role: 'user',
			content: messageText,
			timestamp: new Date()
		};

		messages = [...messages, userMessage];
		scrollToBottom();

		sendingMessage = true;
		error = null;

		try {
			const result: ChatResponse = await apiClient.claude.chat({
				message: messageText,
				session_id: selectedSession?.session_id,
				dangerously_skip_permissions: true // Enable for automated testing
			});

			// Add assistant response
			const assistantMessage: Message = {
				role: 'assistant',
				content: result.response,
				timestamp: new Date()
			};

			messages = [...messages, assistantMessage];

			// Update selected session ID if this was a new chat
			if (!selectedSession && result.session_id) {
				// Optionally reload sessions to show the new session
				await loadSessions();
			}

			scrollToBottom();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to send message';
			console.error('Error sending message:', err);

			// Add error message
			const errorMessage: Message = {
				role: 'assistant',
				content: `Error: ${error}`,
				timestamp: new Date()
			};
			messages = [...messages, errorMessage];
		} finally {
			sendingMessage = false;
		}
	}

	function scrollToBottom() {
		setTimeout(() => {
			messagesEndRef?.scrollIntoView({ behavior: 'smooth' });
		}, 100);
	}
</script>

<div class="flex h-screen flex-col bg-gray-50">
	<!-- Header -->
	<header class="border-b bg-white px-6 py-4">
		<h1 class="text-2xl font-bold text-gray-900">Pocket Claude</h1>
		{#if selectedSession}
			<p class="text-sm text-gray-600">Session: {selectedSession.session_id.slice(0, 8)}...</p>
		{:else}
			<p class="text-sm text-gray-600">New conversation</p>
		{/if}
	</header>

	<!-- Main content -->
	<div class="flex flex-1 overflow-hidden">
		<!-- Sessions sidebar -->
		<aside class="w-80 border-r bg-white p-4">
			<SessionSelector
				{sessions}
				{selectedSession}
				onSelectSession={handleSelectSession}
				{loading}
			/>
		</aside>

		<!-- Chat area -->
		<main class="flex flex-1 flex-col">
			<!-- Messages -->
			<div class="flex-1 overflow-y-auto p-4">
				{#if messages.length === 0}
					<div class="flex h-full items-center justify-center">
						<Card class="max-w-md">
							<CardHeader>
								<CardTitle>Welcome to Pocket Claude</CardTitle>
							</CardHeader>
							<CardContent>
								<p class="text-sm text-gray-600">
									Select an existing session from the sidebar or start a new conversation by typing a
									message below.
								</p>
							</CardContent>
						</Card>
					</div>
				{:else}
					<div class="mx-auto max-w-4xl">
						{#each messages as message (message.timestamp.getTime())}
							<ChatMessage
								role={message.role}
								content={message.content}
								timestamp={message.timestamp}
							/>
						{/each}

						<!-- Scroll anchor -->
						<div bind:this={messagesEndRef}></div>
					</div>
				{/if}
			</div>

			<!-- Error message -->
			{#if error}
				<div class="border-t bg-red-50 px-6 py-3">
					<p class="text-sm text-red-600">Error: {error}</p>
				</div>
			{/if}

			<!-- Input -->
			<ChatInput onSendMessage={handleSendMessage} disabled={sendingMessage} />
		</main>
	</div>
</div>

<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { apiClient } from '$lib/api';
	import { PollingAbortedError } from '$lib/api/endpoints/tasks';
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
	
	// Track active polling operations for cleanup
	let pollingAbortController: AbortController | null = null;

	// Load sessions on mount
	onMount(async () => {
		await loadSessions();
	});
	
	// Cleanup polling on component unmount
	onDestroy(() => {
		if (pollingAbortController) {
			pollingAbortController.abort();
			pollingAbortController = null;
		}
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
		
		// Create new abort controller for this request
		pollingAbortController = new AbortController();
		
		// Track status message index to update the correct message
		let statusMessageIndex = -1;

		try {
			// Create async task
			const taskResponse = await apiClient.tasks.createChatTask({
				message: messageText,
				session_id: selectedSession?.session_id,
				dangerously_skip_permissions: false // Keep permissions enabled for user safety
			});

			// Add status message
			const statusMessage: Message = {
				role: 'assistant',
				content: `Processing your request...`,
				timestamp: new Date()
			};
			messages = [...messages, statusMessage];
			statusMessageIndex = messages.length - 1;
			scrollToBottom();

			// Poll for completion with abort signal
			const completedTask = await apiClient.tasks.pollForCompletion(taskResponse.task_id, {
				intervalMs: 2000,
				signal: pollingAbortController.signal,
				onProgress: (task) => {
					// Update status message based on task status
					const statusText =
						task.status === 'running'
							? 'Claude is thinking...'
							: task.status === 'pending'
								? 'Waiting to start...'
								: 'Processing...';

					// Update the specific status message
					if (statusMessageIndex >= 0 && statusMessageIndex < messages.length) {
						messages = [
							...messages.slice(0, statusMessageIndex),
							{
								role: 'assistant',
								content: statusText,
								timestamp: new Date()
							},
							...messages.slice(statusMessageIndex + 1)
						];
					}
				}
			});

			// Remove status message
			if (statusMessageIndex >= 0) {
				messages = messages.filter((_, index) => index !== statusMessageIndex);
			}

			if (completedTask.status === 'completed') {
				if (completedTask.result) {
					const assistantMessage: Message = {
						role: 'assistant',
						content: completedTask.result,
						timestamp: new Date()
					};
					messages = [...messages, assistantMessage];
				} else {
					// Handle edge case where task completed but has no result
					const assistantMessage: Message = {
						role: 'assistant',
						content: 'Task completed but no response was received.',
						timestamp: new Date()
					};
					messages = [...messages, assistantMessage];
				}

				// Update selected session ID if this was a new chat
				if (!selectedSession && completedTask.session_id) {
					await loadSessions();
				}
			} else if (completedTask.status === 'failed') {
				throw new Error(completedTask.error || 'Task failed');
			}

			scrollToBottom();
		} catch (err) {
			// Remove status message on error if it exists
			if (statusMessageIndex >= 0 && statusMessageIndex < messages.length) {
				messages = messages.filter((_, index) => index !== statusMessageIndex);
			}
			
			error = err instanceof Error ? err.message : 'Failed to send message';
			console.error('Error sending message:', err);

			// Add error message only if not aborted
			if (!(err instanceof PollingAbortedError)) {
				const errorMessage: Message = {
					role: 'assistant',
					content: `Error: ${error}`,
					timestamp: new Date()
				};
				messages = [...messages, errorMessage];
			}
		} finally {
			sendingMessage = false;
			pollingAbortController = null;
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

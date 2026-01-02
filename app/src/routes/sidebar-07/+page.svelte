<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import {
		NearOrbitSidebar,
		DashboardView,
		ChatView,
		SettingsView,
		type ViewType,
		type Mission,
		type HistoryItem,
		type ChatMessageType,
		type Integration,
		type ContextFile
	} from '$lib/components/nearorbit/index.js';

	// View state
	let currentView: ViewType = $state('dashboard');
	let selectedMission: Mission | null = $state(null);

	// Chat state
	let chatInput = $state('');
	let isAgentRunning = $state(true);

	// Settings state
	let autoCommit = $state(false);
	let budgetLimit = $state('$5.00');

	// Sample data - Active Missions
	const activeMissions: Mission[] = $state([
		{
			id: '8aF92',
			title: 'Refactor Auth Middleware',
			description: 'Migrating from JWT to PASETO implementation in the rust-backend repo.',
			status: 'active',
			lastActivity: '2s ago',
			terminalPreview: [
				{ type: 'command', content: 'cargo check' },
				{ type: 'success', content: 'Compiling auth-service v0.1.0...' },
				{ type: 'info', content: 'Checking dependencies...' }
			]
		},
		{
			id: '3bC11',
			title: 'Update Documentation',
			description: 'Scanning all endpoints and regenerating OpenAPI specs.',
			status: 'paused',
			error: 'Waiting for user input'
		}
	]);

	// Sample data - History Items
	const historyItems: HistoryItem[] = $state([
		{
			id: 'h1',
			title: 'Fix CSS Grid Bug',
			status: 'completed',
			completedAt: '2 hours ago',
			duration: '14m'
		},
		{
			id: 'h2',
			title: 'Deploy to Staging',
			status: 'failed',
			completedAt: '4 hours ago',
			duration: '2m',
			error: 'Network Timeout'
		}
	]);

	// Sample data - Chat Messages
	const chatMessages: ChatMessageType[] = $state([
		{
			id: 'm1',
			type: 'user',
			content:
				'Please replace the JWT implementation in <code>src/auth.rs</code> with PASETO v4 local tokens. Ensure we keep the same claims structure.'
		},
		{
			id: 'm2',
			type: 'agent',
			content:
				"The <code>paseto</code> crate isn't listed in your dependencies yet. I'll add it now and then start drafting the new token struct.",
			thought:
				'I need to first inspect the current dependencies to see if `paseto` crate is available, then locate the JWT struct definitions.',
			terminal: {
				title: 'Terminal',
				cwd: '~/projects/rust-backend',
				lines: [
					{ type: 'command', content: 'cat Cargo.toml' },
					{ type: 'info', content: '...' },
					{ type: 'output', content: '[dependencies]' },
					{ type: 'output', content: 'actix-web = "4.0"' },
					{ type: 'output', content: 'jsonwebtoken = "8.1"' },
					{ type: 'output', content: 'serde = { version = "1.0", features = ["derive"] }' }
				]
			}
		},
		{
			id: 'm3',
			type: 'agent',
			content: '',
			isLive: true,
			terminal: {
				title: 'Terminal',
				cwd: '~/projects/rust-backend',
				lines: [{ type: 'command', content: 'cargo add paseto' }],
				isActive: true
			}
		}
	]);

	// Sample data - Context Files
	const contextFiles: ContextFile[] = $state([
		{ name: 'src/auth.rs', path: 'src/auth.rs' },
		{ name: 'Cargo.toml', path: 'Cargo.toml' }
	]);

	// Sample data - Integrations
	const integrations: Integration[] = $state([
		{
			provider: 'github',
			name: 'GitHub',
			status: 'connected',
			username: 'ixian-dev'
		},
		{
			provider: 'gitlab',
			name: 'GitLab',
			status: 'disconnected'
		},
		{
			provider: 'gitea',
			name: 'Gitea / Forgejo',
			status: 'configuring',
			instanceUrl: 'https://git.home.arpa'
		}
	]);

	/**
	 * Get the page title based on current view
	 */
	const pageTitle = $derived(() => {
		switch (currentView) {
			case 'dashboard':
				return 'Active Missions';
			case 'chat':
				return 'Mission Control';
			case 'settings':
				return 'Configuration';
			default:
				return 'Near Orbit';
		}
	});

	/**
	 * Handle navigation from sidebar
	 */
	function handleNavigate(view: ViewType) {
		currentView = view;
		if (view !== 'chat') {
			selectedMission = null;
		}
	}

	/**
	 * Handle opening a mission from dashboard
	 */
	function handleOpenMission(mission: Mission) {
		selectedMission = mission;
		currentView = 'chat';
	}

	/**
	 * Handle going back from chat view
	 */
	function handleBack() {
		currentView = 'dashboard';
		selectedMission = null;
	}

	/**
	 * Handle sending a message
	 */
	function handleSendMessage(message: string) {
		// Add user message
		chatMessages.push({
			id: `m${Date.now()}`,
			type: 'user',
			content: message
		});
		chatInput = '';
	}

	/**
	 * Handle stopping the agent
	 */
	function handleStopAgent() {
		isAgentRunning = false;
	}

	/**
	 * Handle creating a new mission
	 */
	function handleNewMission() {
		// This would open a modal or navigate to new mission creation
		console.log('Create new mission');
	}
</script>

<Sidebar.Provider>
	<NearOrbitSidebar activeView={currentView} onnavigate={handleNavigate} />

	<Sidebar.Inset class="bg-[#09090b]">
		<!-- Header -->
		<header
			class="h-16 border-b border-zinc-800 flex items-center justify-between px-6 bg-[#09090b]/80 backdrop-blur z-10 shrink-0"
		>
			<div class="flex items-center gap-2">
				<Sidebar.Trigger class="-ms-1 text-zinc-400 hover:text-white" />
				<h2 class="text-lg font-medium text-white ml-2">{pageTitle()}</h2>
			</div>
			<div class="flex items-center gap-4">
				<Button
					class="flex items-center gap-2 bg-teal-400 text-zinc-900 hover:bg-teal-300"
					onclick={handleNewMission}
				>
					<PlusIcon class="w-4 h-4" />
					<span class="hidden sm:inline">New Mission</span>
				</Button>
			</div>
		</header>

		<!-- Main Content Area -->
		<main class="flex-1 flex flex-col overflow-hidden">
			{#if currentView === 'dashboard'}
				<DashboardView
					{activeMissions}
					{historyItems}
					onopenmission={handleOpenMission}
				/>
			{:else if currentView === 'chat'}
				<ChatView
					mission={selectedMission ?? activeMissions[0]}
					messages={chatMessages}
					{contextFiles}
					inputValue={chatInput}
					{isAgentRunning}
					onback={handleBack}
					onsend={handleSendMessage}
					onstop={handleStopAgent}
					oninput={(value) => (chatInput = value)}
				/>
			{:else if currentView === 'settings'}
				<SettingsView
					{integrations}
					{autoCommit}
					{budgetLimit}
					onautocommittoggle={(enabled) => (autoCommit = enabled)}
				/>
			{/if}
		</main>
	</Sidebar.Inset>
</Sidebar.Provider>

<style>
	:global(body) {
		background-color: #09090b;
	}
</style>

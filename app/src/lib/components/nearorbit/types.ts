/**
 * Near Orbit Component Types
 * Type definitions for the Near Orbit agent control UI
 */

/** Mission status indicators */
export type MissionStatus = 'active' | 'paused' | 'completed' | 'failed';

/** Navigation view types */
export type ViewType = 'dashboard' | 'chat' | 'settings';

/** Mission data structure */
export interface Mission {
	id: string;
	title: string;
	description: string;
	status: MissionStatus;
	terminalPreview?: TerminalLine[];
	lastActivity?: string;
	duration?: string;
	error?: string;
}

/** Terminal output line */
export interface TerminalLine {
	type: 'command' | 'output' | 'success' | 'error' | 'info';
	content: string;
}

/** Chat message types */
export type MessageType = 'user' | 'agent';

/** Chat message structure */
export interface ChatMessage {
	id: string;
	type: MessageType;
	content: string;
	thought?: string;
	terminal?: TerminalBlock;
	timestamp?: Date;
	isLive?: boolean;
}

/** Terminal block for chat messages */
export interface TerminalBlock {
	title?: string;
	cwd?: string;
	lines: TerminalLine[];
	isActive?: boolean;
}

/** Context file pill */
export interface ContextFile {
	name: string;
	path: string;
}

/** Integration provider types */
export type IntegrationProvider = 'github' | 'gitlab' | 'gitea';

/** Integration connection status */
export type IntegrationStatus = 'connected' | 'disconnected' | 'configuring';

/** Integration data structure */
export interface Integration {
	provider: IntegrationProvider;
	name: string;
	status: IntegrationStatus;
	username?: string;
	instanceUrl?: string;
}

/** Server status for sidebar */
export interface ServerStatus {
	name: string;
	isOnline: boolean;
	cpuUsage?: string;
	memoryUsage?: string;
}

/** Navigation item for sidebar */
export interface NavItem {
	id: ViewType;
	label: string;
	icon: 'missions' | 'settings';
}

/** History item for dashboard */
export interface HistoryItem {
	id: string;
	title: string;
	status: 'completed' | 'failed';
	completedAt: string;
	duration: string;
	error?: string;
}

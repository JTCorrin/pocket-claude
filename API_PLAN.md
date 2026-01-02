# Claude Code API Service Specification

## Overview

A FastAPI service that wraps Claude Code CLI, enabling HTTP-based interaction with Claude Code sessions. Designed for internal network access via WireGuard VPN.

---

## Environment

- **Host**: Ubuntu VM with Claude Code installed
- **Auth**: API key stored in `ANTHROPIC_API_KEY` environment variable
- **Claude data**: `~/.claude/` directory contains session history
- **Default port**: 8000 (or configurable)

---

## Endpoints

### 1. `GET /sessions`

List available Claude Code sessions that can be resumed.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Max sessions to return |
| `project` | string | null | Filter by project path |

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "3298a122-7fa3-41b6-a60a-304cd81a9d0a",
      "project": "/Users/joecorrin/Development/Capacitor/ixian-mission-critical",
      "preview": "First message preview text...",
      "last_active": "2025-01-02T09:38:00Z",
      "message_count": 12
    }
  ]
}
```

**Implementation Notes:**
- Parse `~/.claude/projects/` directory
- Each project folder contains `.jsonl` session files
- Extract first user message as preview
- Session files are JSONL format; look for `type: "user"` entries

---

### 2. `POST /chat`

Send a message to Claude Code, optionally resuming an existing session.

**Request Body:**
```json
{
  "message": "Your prompt or question here",
  "session_id": "3298a122-7fa3-41b6-a60a-304cd81a9d0a",  // optional
  "project_path": "/path/to/project",                     // optional
  "dangerously_skip_permissions": false                   // optional, default false
}
```

**Response:**
```json
{
  "response": "Claude's response text...",
  "session_id": "3298a122-7fa3-41b6-a60a-304cd81a9d0a",
  "exit_code": 0,
  "stderr": ""
}
```

**Implementation Notes:**
- Execute via `subprocess`:
  ```python
  cmd = ["claude", "-p", message]
  if session_id:
      cmd.extend(["--resume", session_id])
  if dangerously_skip_permissions:
      cmd.append("--dangerously-skip-permissions")
  
  result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)
  ```
- Consider timeout handling for long-running operations
- `--dangerously-skip-permissions` allows automated file operations (use with caution)

---

### 3. `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "claude_version": "2.0.76",
  "api_key_configured": true
}
```

**Implementation Notes:**
- Run `claude --version` to get version
- Check `ANTHROPIC_API_KEY` is set

---

### 4. `GET /projects`

List known projects (directories Claude Code has been used in).

**Response:**
```json
{
  "projects": [
    {
      "path": "/Users/joecorrin/Development/Capacitor/ixian-mission-critical",
      "session_count": 235,
      "last_active": "2025-01-02T09:38:00Z"
    }
  ]
}
```

**Implementation Notes:**
- Read `~/.claude/projects/` directory
- Folder names use `-` as path separator (e.g., `-Users-joecorrin-Dev` → `/Users/joecorrin/Dev`)

---

## Session File Format Reference

Location: `~/.claude/projects/{project-name}/{session-id}.jsonl`

Each line is a JSON object. Relevant types:

```jsonl
{"type":"user","message":{"role":"user","content":"..."},"sessionId":"...","timestamp":"..."}
{"type":"file-history-snapshot","messageId":"...","snapshot":{...}}
{"type":"queue-operation","operation":"dequeue","timestamp":"...","sessionId":"..."}
```

For listing sessions, filter for `type: "user"` entries to get conversation content.

---

## Security Considerations

1. **Internal only**: Bind to private IP or localhost; access via WireGuard
2. **No auth in v1**: Rely on network-level security (VPN). Add API key auth later if needed.
3. **Rate limiting**: Consider adding basic rate limiting
4. **Input validation**: Sanitize `project_path` to prevent path traversal

---

## Optional Future Endpoints

| Endpoint | Purpose |
|----------|---------|
| `DELETE /sessions/{id}` | Delete a session |
| `GET /sessions/{id}/messages` | Get full conversation history |
| `POST /chat/stream` | SSE streaming responses |
| `WebSocket /ws/chat` | Real-time bidirectional chat |

---

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn

# Run service
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Example Usage

```bash
# List sessions
curl http://claude-api.home.lan:8000/sessions

# Send a message
curl -X POST http://claude-api.home.lan:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain the main function in this project"}'

# Resume a session
curl -X POST http://claude-api.home.lan:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Continue where we left off", "session_id": "3298a122-..."}'
```
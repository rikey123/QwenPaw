# Ralph Loop

Ralph Loop is a **self-referential development loop**. When you use the `/ralph-loop`
command with a task description, the agent works on the task, checks if its done
after each iteration, and if not, automatically continues until the task is
complete, the maximum iteration limit is reached, or you cancel it manually.

Ralph Loop runs in the [Console](./console) only (not yet available in channels).
It is inspired by [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent).

---

## Usage

### Start a Ralph Loop

```
/ralph-loop <task description>
```

**Examples:**

```
/ralph-loop Write a Python script that fetches weather data from an API
/ralph-loop Create a React component for a file uploader with drag-and-drop
```

### Set max iterations

By default the loop stops after **20 iterations**. You can set a custom limit:

```
/ralph-loop --max-iterations=10 Implement a sorting algorithm visualization
```

### Cancel a running loop

To stop an active loop at any time:

```
/cancel-loop
```

If no loop is running, you will see `No active Ralph Loop to cancel.`

---

## How It Works

1. **Initial prompt** -- The agent receives the task description along with a
   system prompt explaining the loop rules and how to signal completion.
2. **Work iteration** -- The agent works on the task using all available tools.
3. **Completion check** -- After each iteration, the system checks whether the
   agent has signaled completion. The agent signals completion by setting a
   `completed` flag in its response metadata.
4. **Continue or stop** -- If not done, a continuation prompt is injected
   reminding the agent of the task and current iteration count, then the next
   iteration begins. If the task is done, or if the iteration limit is reached,
   the loop ends.

### Console progress

While a Ralph Loop is running, the Console shows live progress with the current
iteration count and status (running, completed, cancelled, or max iterations
reached).

---

## Completion Criteria

The loop stops when any of these conditions is met:

| Condition | Description |
| --------- | ----------- |
| **Task completed** | The agent signals completion in its response metadata |
| **Max iterations** | The loop hits the iteration limit (default 20, configurable via `--max-iterations`) |
| **Manual cancel** | You send `/cancel-loop` to stop an active loop |

---

## Important Notes

- **Console only** -- Ralph Loop is available in the Console but not yet in
  channels (DingTalk, Feishu, WeChat, etc.).
- **Auto-continue disabled** -- During a Ralph Loop, the system's automatic
  continuation (`auto_continue_on_text_only`) is temporarily disabled to prevent
  nested loops. It is restored when the loop finishes or is cancelled.
- **Duplicate protection** -- If a Ralph Loop is already running in the current
  session, a second `/ralph-loop` command will not start a new loop.
- **Memory only** -- Loop state is kept in memory only. No files are written to
  disk (except any files the agent creates as part of the task).
- **Task validation** -- The task description must be at least 5 characters long.
  Meta-questions (e.g. "what is ralph loop?") are rejected.

---

## Comparison with Other Modes

| Mode | Use Case | Agent Behavior |
| ---- | -------- | -------------- |
| **Normal Chat** | Simple tasks, quick fixes | Single interaction, responds once |
| **Plan Mode** | Structured multi-step tasks | Creates a plan, executes subtasks in order |
| **Ralph Loop** | Iterative tasks that need multiple attempts | Repeats until done or limit reached |
| **Mission Mode** | Complex, long-running tasks | Master dispatches workers, verifiers validate |

---

## Related Pages

- [Introduction](./intro) -- What QwenPaw can do
- [Console](./console) -- Web UI and agent switching
- [Magic Commands](./commands) -- `/plan`, `/clear`, `/new`, and more
- [Plan Mode](./plan) -- Structured task decomposition
- [Mission Mode](./commands#mission-mode) -- Autonomous execution for complex tasks

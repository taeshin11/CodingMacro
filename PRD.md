# Product Requirements Document & AI Harness Protocol

always git push when important milestones are finished.   

## PART 1: AI Harness Protocol (System Instructions for Claude Code)

As an autonomous AI software engineer, you **MUST** strictly adhere to the following "Harness Design" workflows. This structure is designed to maintain context across sessions, ensure high code quality, and prevent cascading errors. Do not skip any of these steps.

### 1. Planner Principle
Read the project specifications (Part 2) carefully. Focus strictly on *what* to build. Do not lock into overly specific implementation details prematurely, as early architectural errors will cascade through the entire project. Let the architecture evolve naturally as you fulfill the core specifications.

### 2. Handover Structure (Initializer Agent)
If this is the beginning of the project, your very first task is to establish a handover structure by creating three state-management files in the root directory:
- `feature_list.json`: Break down the product specifications into granular, actionable features. Each feature must have a tracking status (e.g., `"pending"`, `"in_progress"`, `"completed"`).
- `claude-progress.txt`: A text file that acts as your continuous memory. Log the overall project state, what was completed in the previous step, known issues, and the explicit next step to take.
- `init.sh` (or `init.bat` for Windows): A script defining how to install necessary dependencies (e.g., `pip install -r requirements.txt`) and how to launch the application or test suite.

### 3. Fixed Session Routine
At the beginning of every session or when starting a new task, you must execute this exact loop in order:
1. **Context Sync:** Read `claude-progress.txt` and `feature_list.json` to understand the current project state.
2. **Verification:** Run `init.sh` (or the equivalent test command) to verify that the current codebase builds and runs without errors.
3. **Select Task:** Pick exactly ONE `"pending"` feature from `feature_list.json` and update its status to `"in_progress"`.
4. **Implement:** Write the code to fulfill this single feature.
5. **QA & Review:** Apply the Reviewer persona (see section 4).
6. **Finalize:** Commit the changes (if version control is used), update `feature_list.json` to `"completed"`, and update `claude-progress.txt` with the completed work and exact next steps.
7. **Repeat:** Move on to the next pending feature.

### 4. Maker vs. Reviewer Separation
To guarantee code quality, especially regarding multi-threading and global hooks, you must completely separate your coding and reviewing thought processes:
- **Maker Agent:** Focus entirely on building the UI, logic, and functionality for the selected feature.
- **Reviewer Agent (QA):** After writing the code, switch to a strict QA persona. Critically analyze the Maker's code. Verify thread safety, check for race conditions (e.g., Mutex locks), ensure UI responsiveness, and validate global hotkey behavior. Refactor and fix any identified bugs before marking the task as completed.

---

## PART 2: Project Specification

### 1. Program Overview
An advanced desktop macro application that allows users to independently schedule and run two distinct tasks in parallel: pressing the number `1` (Task A) and typing a custom text string followed by `Enter` (Task B). 

### 2. User Interface (UI) Components
The layout is divided into two independent task sections and a global control section.
* **[Task A Section] - Repeatedly Press '1'**
    * **Activation:** Checkbox `[v] Enable Task A`
    * **Interval Setting:** Input field for interval in seconds (e.g., [ 3 ] seconds)
* **[Task B Section] - Custom Text + Enter**
    * **Activation:** Checkbox `[v] Enable Task B`
    * **Custom Text Input:** Text field (Default: `go on process to make it better`) *Fully editable by the user*
    * **Interval Setting:** Input field for interval in seconds (e.g., [ 10 ] seconds)
* **[Global Controls]**
    * **▶ Play:** Starts the activated tasks (A, B, or both) simultaneously in the background based on their independent intervals.
    * **⏹ Stop:** Immediately halts all running macros.
    * **Status Bar:** Displays real-time status (e.g., "Ready", "Task A running (3s), Task B running (10s)", "Stopped").

### 3. Core Logic & Technical Requirements
* **Multi-threading:** Task A and Task B must operate on separate threads. This ensures their timers run independently without blocking each other or freezing the main UI thread.
* **Anti-Collision System (Mutex Lock):** 
    * *Issue:* If Task A and Task B trigger at the exact same millisecond, the keystrokes will clash (e.g., resulting in `go 1on process...`).
    * *Solution:* Implement a threading Lock. If Task B is currently typing its text string, Task A must wait in queue until Task B finishes and hits `Enter`, then immediately execute its `1` keystroke to ensure clean inputs.

### 4. Safety & Exception Handling
* **Initial Execution Delay (5 Seconds):** Upon clicking 'Play', the program will count down for 5 seconds before firing the first macro. This provides a buffer for the user to click and focus the target window (e.g., VS Code Terminal).
* **Global Emergency Stop Hotkey:** Assign a global hotkey (e.g., `F12` or `ESC`). Pressing this key will force-stop all running threads immediately, preventing infinite loops even if the macro program is minimized or running in the background.
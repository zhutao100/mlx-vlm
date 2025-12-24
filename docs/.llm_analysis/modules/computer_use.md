# Computer Use Agent Analysis

## Architecture
**Type**: Dual-Model Autonomous GUI Agent.
**Components**:
1.  **Planner Model** (e.g., `Qwen2.5-VL-7B`):
    -   Role: High-level reasoning.
    -   Input: Screenshot + Task + History.
    -   Output: Structured plan (Thought + Action verb).
2.  **Grounding Model** (e.g., `ShowUI-2B`):
    -   Role: Precise coordinate generation.
    -   Input: Screenshot + Planner's intent.
    -   Output: Exact `{x, y}` coordinates or element bounding boxes.
3.  **Executor**:
    -   Uses `pyautogui` to perform system actions (click, type, scroll).
    -   Visualizes actions using transparent `tkinter` overlays (red dots/text) for user feedback.

## Workflow
1.  **Observe**: Capture screen using `PIL.ImageGrab`.
2.  **Plan**: Planner model generates the next step (e.g., "Click the Search bar").
3.  **Ground**: GUI model translates "Search bar" into pixel coordinates.
4.  **Act**: Executor moves mouse/types.
5.  **Loop**: Repeats until task completion or failure.

## Key Files
- `autonomous_gui_agent.py`: Main agent loop and `process_command`.
- `utils.py`: Drawing helpers and history logging (`pandas`).

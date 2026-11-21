"""Local browser interface for the Smart Study Assistant.

The HTTP handlers call the same Python functions registered as MCP tools,
resources, and prompts in server.py. The browser does not speak MCP directly.
"""

import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import server as mcp_server


PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f7f7f3">
  <title>Smart Study Assistant</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #202a36;
      --muted: #6f7b87;
      --line: #e7e9e5;
      --paper: #fff;
      --canvas: #f7f7f3;
      --teal: #147d73;
      --teal-dark: #0e625a;
      --teal-soft: #e8f4f1;
      --gold: #e7b961;
      --shadow: 0 14px 36px rgba(34, 50, 61, .055);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; background: var(--canvas); color: var(--ink);
      font: 15px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button, input { font: inherit; }
    button { cursor: pointer; }
    .topbar { height: 76px; display: flex; align-items: center; justify-content: space-between; padding: 0 max(5vw, 24px); background: rgba(255,255,255,.88); border-bottom: 1px solid var(--line); }
    .brand { display: flex; align-items: center; gap: 12px; color: var(--ink); text-decoration: none; font-weight: 720; letter-spacing: -.025em; }
    .brand-mark { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 12px; background: var(--teal); color: white; font-size: 19px; }
    .nav { display: flex; gap: 28px; }
    .nav a { color: var(--muted); text-decoration: none; font-size: 13px; font-weight: 600; }
    .nav a:hover { color: var(--teal); }
    main { width: min(1080px, calc(100% - 48px)); margin: 54px auto 76px; }
    .hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; margin-bottom: 34px; }
    .eyebrow { color: var(--teal); font-size: 11px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
    h1 { margin: 8px 0 9px; font-size: clamp(34px, 5vw, 51px); line-height: 1.08; letter-spacing: -.055em; font-weight: 690; }
    .hero p { margin: 0; color: var(--muted); font-size: 15px; }
    .date-chip { flex: 0 0 auto; padding: 10px 15px; border: 1px solid var(--line); border-radius: 999px; color: #53616d; background: var(--paper); font-size: 12px; font-weight: 650; }
    .layout { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(280px, .85fr); gap: 22px; align-items: start; }
    .stack { display: grid; gap: 22px; }
    .card { background: var(--paper); border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); }
    .card-pad { padding: 24px; }
    .section-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    h2 { margin: 0; font-size: 18px; letter-spacing: -.025em; }
    .subhead { color: var(--muted); font-size: 12px; margin: 4px 0 0; }
    .count { min-width: 34px; height: 30px; display: grid; place-items: center; border-radius: 9px; background: var(--teal-soft); color: var(--teal-dark); font-size: 12px; font-weight: 750; }
    .add-form { display: flex; gap: 10px; margin: 22px 0 14px; }
    .add-form input, .plan-form input { min-width: 0; width: 100%; padding: 12px 14px; outline: none; color: var(--ink); background: #fcfcfa; border: 1px solid var(--line); border-radius: 10px; }
    .add-form input:focus, .plan-form input:focus { border-color: #70b2a8; box-shadow: 0 0 0 3px rgba(20,125,115,.1); }
    .primary { border: 0; border-radius: 10px; padding: 11px 16px; color: #fff; background: var(--teal); font-weight: 680; white-space: nowrap; transition: background .15s, transform .15s; }
    .primary:hover { background: var(--teal-dark); transform: translateY(-1px); }
    .task-list { display: grid; }
    .task-row { display: flex; align-items: center; gap: 13px; padding: 14px 2px; border-top: 1px solid #f0f1ed; }
    .task-toggle { flex: 0 0 auto; width: 22px; height: 22px; display: grid; place-items: center; border: 1.5px solid #cbd2ce; border-radius: 7px; color: white; background: #fff; }
    .task-toggle:hover { border-color: var(--teal); }
    .task-toggle.done { border-color: var(--teal); background: var(--teal); }
    .task-copy { min-width: 0; flex: 1; }
    .task-name { display: block; overflow-wrap: anywhere; font-weight: 600; }
    .task-meta { color: var(--muted); font-size: 11px; }
    .task-row.completed .task-name { color: #89938f; text-decoration: line-through; }
    .empty { padding: 25px 8px 8px; text-align: center; color: var(--muted); font-size: 13px; }
    .guide-card { position: relative; overflow: hidden; background: #edf6f2; border-color: #e2eee9; }
    .guide-card::after { position: absolute; content: ""; width: 115px; height: 115px; right: -44px; top: -50px; border: 1px solid rgba(20,125,115,.12); border-radius: 50%; box-shadow: 0 0 0 14px rgba(20,125,115,.035), 0 0 0 29px rgba(20,125,115,.025); }
    .guide-icon { width: 37px; height: 37px; display: grid; place-items: center; border-radius: 12px; background: white; color: var(--teal); font-size: 18px; }
    .guide-card h2 { margin-top: 15px; }
    .guide-text { margin: 8px 0 0; color: #52655f; font-size: 13px; line-height: 1.75; }
    .plan-form { display: grid; gap: 12px; margin-top: 18px; }
    .plan-form label { display: grid; gap: 6px; color: #56616b; font-size: 12px; font-weight: 650; }
    .plan-form .primary { justify-self: start; }
    .plan-result { display: grid; gap: 14px; margin: 18px 0 0; padding: 18px; border: 1px solid #e4ebe6; border-radius: 14px; background: #f8faf8; color: #45534e; }
    .plan-result.hidden { display: none; }
    .plan-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
    .plan-heading h3 { margin: 0; color: var(--ink); font-size: 16px; line-height: 1.35; overflow-wrap: anywhere; }
    .plan-duration { flex: 0 0 auto; padding: 5px 9px; border-radius: 999px; color: var(--teal-dark); background: var(--teal-soft); font-size: 11px; font-weight: 750; }
    .goal-box { padding: 12px 14px; border-left: 3px solid var(--gold); border-radius: 0 9px 9px 0; background: #fffaf0; }
    .plan-label { display: block; margin-bottom: 4px; color: #78837e; font-size: 10px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
    .goal-box p { margin: 0; color: #4f5d56; font-size: 12px; line-height: 1.6; }
    .plan-timeline { display: grid; gap: 8px; }
    .plan-block { display: grid; grid-template-columns: 70px 1fr; gap: 10px; align-items: start; padding: 10px 11px; border: 1px solid #edf0ec; border-radius: 10px; background: white; }
    .plan-time { padding-top: 2px; color: var(--teal-dark); font-size: 10px; font-weight: 750; font-variant-numeric: tabular-nums; }
    .plan-block h4 { margin: 0; color: #34413b; font-size: 12px; }
    .plan-block p { margin: 3px 0 0; color: var(--muted); font-size: 11px; line-height: 1.5; }
    .plan-note { margin: 0; color: #89938f; font-size: 10px; }
    .hidden { display: none; }
    .toast { position: fixed; bottom: 22px; left: 50%; transform: translate(-50%, 12px); padding: 11px 16px; border-radius: 10px; color: white; background: #263941; box-shadow: var(--shadow); opacity: 0; pointer-events: none; transition: .2s; font-size: 13px; }
    .toast.show { transform: translate(-50%, 0); opacity: 1; }
    footer { margin-top: 34px; color: #96a09c; text-align: center; font-size: 11px; }
    @media (max-width: 760px) {
      .topbar { height: 66px; }
      .nav { gap: 15px; }
      .nav a { font-size: 12px; }
      main { margin-top: 36px; }
      .layout { grid-template-columns: 1fr; }
      .hero { align-items: flex-start; }
      .date-chip { display: none; }
    }
    @media (max-width: 470px) {
      .topbar { padding: 0 18px; }
      .nav { gap: 11px; }
      .nav a { font-size: 11px; }
      main { width: calc(100% - 32px); }
      .card-pad { padding: 19px; }
      .add-form { flex-direction: column; }
      .add-form .primary { width: 100%; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="#top"><span class="brand-mark" aria-hidden="true">✦</span><span>Smart Study</span></a>
    <nav class="nav" aria-label="Main navigation">
      <a href="#tasks">Tasks</a><a href="#guide">Study guide</a><a href="#planner">Study plan</a>
    </nav>
  </header>
  <main id="top">
    <section class="hero">
      <div><div class="eyebrow">Your study space</div><h1>Make room for<br>focused learning.</h1><p>A little progress, made consistently, adds up.</p></div>
      <div class="date-chip" id="today"></div>
    </section>
    <div class="layout">
      <section class="card card-pad" id="tasks">
        <div class="section-head"><div><h2>Your tasks</h2><p class="subhead">Keep your next steps clear and manageable.</p></div><span class="count" id="task-count" aria-label="Open tasks">0</span></div>
        <form class="add-form" id="add-form"><input id="task-input" type="text" maxlength="300" placeholder="What would you like to study?" aria-label="New study task" required><button class="primary" type="submit">Add task <span aria-hidden="true">＋</span></button></form>
        <div class="task-list" id="task-list" aria-live="polite"></div>
      </section>
      <div class="stack">
        <section class="card card-pad guide-card" id="guide">
          <div class="guide-icon" aria-hidden="true">✎</div><h2>A thoughtful reminder</h2>
          <p class="guide-text" id="guide-text">Loading your study guide…</p>
        </section>
        <section class="card card-pad" id="planner">
          <div class="section-head"><div><h2>Plan a study session</h2><p class="subhead">Get a focused outline for what you’re learning.</p></div></div>
          <form class="plan-form" id="plan-form">
            <label>Topic<input id="topic-input" type="text" maxlength="200" placeholder="e.g. Photosynthesis" required></label>
            <label>Available time (minutes)<input id="minutes-input" type="number" min="15" max="600" value="30" required></label>
            <button class="primary" type="submit">Create study plan</button>
          </form>
          <div class="plan-result hidden" id="plan-result" aria-live="polite"></div>
        </section>
      </div>
    </div>
    <footer>Your tasks are saved locally on this computer.</footer>
  </main>
  <div class="toast" id="toast" role="status" aria-live="polite"></div>
  <script>
    const taskList = document.querySelector('#task-list');
    const toast = document.querySelector('#toast');
    let toastTimer;

    document.querySelector('#today').textContent = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'long', day: 'numeric' }).format(new Date());

    async function request(path, options = {}) {
      const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Something went wrong.');
      return data;
    }

    function showToast(message) {
      toast.textContent = message;
      toast.classList.add('show');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
    }

    function renderTasks(tasks) {
      taskList.replaceChildren();
      const openCount = tasks.filter(task => !task.completed).length;
      document.querySelector('#task-count').textContent = openCount;
      if (!tasks.length) {
        const empty = document.createElement('div');
        empty.className = 'empty';
        empty.textContent = 'Your list is clear. Add a task to get started.';
        taskList.append(empty);
        return;
      }
      for (const task of tasks) {
        const row = document.createElement('div');
        row.className = `task-row${task.completed ? ' completed' : ''}`;
        const button = document.createElement('button');
        button.className = `task-toggle${task.completed ? ' done' : ''}`;
        button.type = 'button';
        button.setAttribute('aria-label', task.completed ? `Task ${task.id} completed` : `Mark ${task.task} completed`);
        button.title = task.completed ? 'Completed' : 'Mark completed';
        button.textContent = task.completed ? '✓' : '';
        if (!task.completed) button.addEventListener('click', () => completeTask(task.id));
        const copy = document.createElement('div');
        copy.className = 'task-copy';
        const name = document.createElement('span');
        name.className = 'task-name';
        name.textContent = task.task;
        const meta = document.createElement('span');
        meta.className = 'task-meta';
        meta.textContent = `Task ${task.id} · ${task.completed ? 'Completed' : 'In progress'}`;
        copy.append(name, meta);
        row.append(button, copy);
        taskList.append(row);
      }
    }

    async function refreshTasks() {
      const data = await request('/api/tasks');
      renderTasks(data.tasks);
    }

    async function completeTask(taskId) {
      try {
        await request(`/api/tasks/${taskId}/complete`, { method: 'POST', body: '{}' });
        await refreshTasks();
        showToast('Task marked complete. Nice work.');
      } catch (error) { showToast(error.message); }
    }

    function renderStudyPlan(plan) {
      const output = document.querySelector('#plan-result');
      output.replaceChildren();

      const heading = document.createElement('div');
      heading.className = 'plan-heading';
      const title = document.createElement('h3');
      title.textContent = plan.topic;
      const duration = document.createElement('span');
      duration.className = 'plan-duration';
      duration.textContent = `${plan.total_minutes} minutes`;
      heading.append(title, duration);

      const goal = document.createElement('div');
      goal.className = 'goal-box';
      const goalLabel = document.createElement('span');
      goalLabel.className = 'plan-label';
      goalLabel.textContent = 'Learning goal';
      const goalText = document.createElement('p');
      goalText.textContent = plan.learning_goal;
      goal.append(goalLabel, goalText);

      const timeline = document.createElement('div');
      timeline.className = 'plan-timeline';
      const formatMinute = minute => String(minute).padStart(2, '0');
      for (const block of plan.blocks) {
        const item = document.createElement('article');
        item.className = 'plan-block';
        const time = document.createElement('div');
        time.className = 'plan-time';
        time.textContent = `${formatMinute(block.start_minute)}–${formatMinute(block.end_minute)} min`;
        const description = document.createElement('div');
        const blockTitle = document.createElement('h4');
        blockTitle.textContent = block.title;
        const detail = document.createElement('p');
        detail.textContent = block.detail;
        description.append(blockTitle, detail);
        item.append(time, description);
        timeline.append(item);
      }

      const note = document.createElement('p');
      note.className = 'plan-note';
      note.textContent = 'Template-based plan · No AI model was called.';
      output.append(heading, goal, timeline, note);
      output.classList.remove('hidden');
    }

    document.querySelector('#add-form').addEventListener('submit', async event => {
      event.preventDefault();
      const input = document.querySelector('#task-input');
      try {
        const data = await request('/api/tasks', { method: 'POST', body: JSON.stringify({ task: input.value }) });
        input.value = '';
        await refreshTasks();
        showToast(data.message);
      } catch (error) { showToast(error.message); }
    });

    document.querySelector('#plan-form').addEventListener('submit', async event => {
      event.preventDefault();
      const topic = document.querySelector('#topic-input').value;
      const available_minutes = Number(document.querySelector('#minutes-input').value);
      try {
        const data = await request('/api/study-plan', { method: 'POST', body: JSON.stringify({ topic, available_minutes }) });
        renderStudyPlan(data.plan);
      } catch (error) { showToast(error.message); }
    });

    async function loadPage() {
      try {
        await Promise.all([refreshTasks(), request('/api/guide').then(data => { document.querySelector('#guide-text').textContent = data.guide; })]);
      } catch (error) { showToast(error.message); }
    }
    loadPage();
  </script>
</body>
</html>
"""


class StudyAssistantHandler(BaseHTTPRequestHandler):
    """Serve the browser page and a small JSON API over localhost."""

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 10_000:
            raise ValueError("Request body must be between 1 and 10000 bytes.")
        body = json.loads(self.rfile.read(length))
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object.")
        return body

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/tasks":
            self._send_json(200, {"tasks": mcp_server.list_tasks()})
        elif path == "/api/guide":
            self._send_json(200, {"guide": mcp_server.study_guide()})
        else:
            self._send_json(404, {"error": "Not found."})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            data = self._read_json()
            if path == "/api/tasks":
                task = data.get("task")
                if not isinstance(task, str):
                    self._send_json(400, {"error": "Task must be text."})
                    return
                message = mcp_server.add_task(task)
                if message == "Task cannot be empty.":
                    self._send_json(400, {"error": message})
                    return
                self._send_json(201, {"message": message, "task": mcp_server.list_tasks()[-1]})
            elif path.startswith("/api/tasks/") and path.endswith("/complete"):
                task_id_text = path.removeprefix("/api/tasks/").removesuffix("/complete").strip("/")
                try:
                    task_id = int(task_id_text)
                except ValueError:
                    self._send_json(400, {"error": "Task ID must be a number."})
                    return
                message = mcp_server.mark_task_completed(task_id)
                if message.startswith("No task found"):
                    self._send_json(404, {"error": message})
                    return
                self._send_json(200, {"message": message})
            elif path == "/api/study-plan":
                topic = data.get("topic")
                minutes = data.get("available_minutes", 30)
                if not isinstance(topic, str) or not topic.strip() or len(topic.strip()) > 200:
                    self._send_json(400, {"error": "Enter a topic between 1 and 200 characters."})
                    return
                if not isinstance(minutes, int) or isinstance(minutes, bool) or not 15 <= minutes <= 600:
                    self._send_json(400, {"error": "Study time must be from 15 to 600 minutes."})
                    return
                self._send_json(200, {"plan": _build_study_plan(topic.strip(), minutes)})
            else:
                self._send_json(404, {"error": "Not found."})
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error) or "Invalid JSON request."})


def _build_study_plan(topic: str, total_minutes: int) -> dict[str, object]:
    """Build a predictable study outline; this does not call an AI model."""
    goal_minutes = min(5, max(2, round(total_minutes * 0.08)))
    test_minutes = min(10, max(3, round(total_minutes * 0.12)))
    break_minutes = min(5, max(2, round(total_minutes * 0.08)))

    focused_minutes = total_minutes - goal_minutes - test_minutes
    break_count = max(1, math.ceil(focused_minutes / 50) - 1)
    study_minutes = focused_minutes - break_count * break_minutes
    study_block_count = break_count + 1
    block_base, block_remainder = divmod(study_minutes, study_block_count)
    study_durations = [
        block_base + (1 if index < block_remainder else 0)
        for index in range(study_block_count)
    ]

    blocks: list[dict[str, object]] = []

    def add_block(title: str, duration: int, detail: str) -> None:
        start_minute = blocks[-1]["end_minute"] if blocks else 0
        end_minute = int(start_minute) + duration
        blocks.append({
            "title": title,
            "duration_minutes": duration,
            "start_minute": start_minute,
            "end_minute": end_minute,
            "detail": detail,
        })

    add_block(
        "Set a learning goal",
        goal_minutes,
        f"Choose one question about {topic} that you want to answer by the end.",
    )
    for index, duration in enumerate(study_durations):
        title = "Study the core ideas" if index == 0 else "Practice and active recall"
        detail = (
            f"Review the key ideas in {topic} and note anything that needs a second look."
            if index == 0
            else f"Recall or apply what you learned about {topic} before checking your notes."
        )
        add_block(title, duration, detail)
        if index < break_count:
            add_block("Short break", break_minutes, "Step away, stretch, and rest your eyes.")
    add_block(
        "Quick self-test",
        test_minutes,
        f"Without notes, explain the key ideas in {topic} or answer a few practice questions.",
    )

    return {
        "topic": topic,
        "total_minutes": total_minutes,
        "learning_goal": f"By the end, explain the main ideas of {topic} in your own words and identify anything to review.",
        "blocks": blocks,
        "generation_method": "template",
    }


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    with ThreadingHTTPServer((host, port), StudyAssistantHandler) as http_server:
        print(f"Smart Study Assistant web interface: http://{host}:{port}")
        print("Press Ctrl+C to stop the web server.")
        try:
            http_server.serve_forever()
        except KeyboardInterrupt:
            print("\nWeb server stopped.")


if __name__ == "__main__":
    main()

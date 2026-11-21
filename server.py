
import json
from pathlib import Path
from threading import RLock
from typing import TypedDict

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Smart Study Assistant")
TASKS_FILE = Path(__file__).with_name("tasks.json")
_tasks_lock = RLock()


class StudyTask(TypedDict):
    id: int
    task: str
    completed: bool


def _load_tasks() -> list[StudyTask]:
    """Load tasks from disk, or start with an empty list on first run."""
    if not TASKS_FILE.exists():
        return []

    with TASKS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("id"), int)
        or not isinstance(item.get("task"), str)
        or not isinstance(item.get("completed"), bool)
        for item in data
    ):
        raise ValueError(f"Invalid task data in {TASKS_FILE}")
    return data


study_tasks: list[StudyTask] = _load_tasks()


def _refresh_tasks() -> None:
    """Refresh the shared in-process list from disk before reading or changing it."""
    study_tasks[:] = _load_tasks()


def _save_tasks() -> None:
    """Write the current task list to disk."""
    temporary_file = TASKS_FILE.with_suffix(".json.tmp")
    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(study_tasks, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temporary_file.replace(TASKS_FILE)


@mcp.tool()
def add_task(task: str) -> str:
    """Add a study task to the persistent task list."""
    task = task.strip()
    if not task:
        return "Task cannot be empty."

    with _tasks_lock:
        _refresh_tasks()
        task_id = max((item["id"] for item in study_tasks), default=0) + 1
        study_tasks.append({"id": task_id, "task": task, "completed": False})
        _save_tasks()
    return f"Task {task_id} added successfully: {task}"


@mcp.tool()
def list_tasks() -> list[StudyTask]:
    """List all study tasks, including their IDs and completion status."""
    with _tasks_lock:
        _refresh_tasks()
        return [item.copy() for item in study_tasks]


@mcp.tool()
def mark_task_completed(task_id: int) -> str:
    """Mark the task with this ID as completed."""
    with _tasks_lock:
        _refresh_tasks()
        for item in study_tasks:
            if item["id"] == task_id:
                if item["completed"]:
                    return f"Task {task_id} is already completed."
                item["completed"] = True
                _save_tasks()
                return f"Task {task_id} marked as completed."
    return f"No task found with ID {task_id}."


@mcp.resource("study://guide")
def study_guide() -> str:
    """A short guide with practical study tips."""
    return (
        "Study guide: Set one clear goal, break it into short sessions, use active recall, "
        "take brief breaks, and review what you learned at the end."
    )


@mcp.resource("study://tasks")
def task_resource() -> str:
    """The persistent study task list."""
    tasks = list_tasks()
    if not tasks:
        return "No study tasks have been added yet."
    lines = []
    for item in tasks:
        status = "completed" if item["completed"] else "not completed"
        lines.append(f"- [{item['id']}] {item['task']} ({status})")
    return "Study tasks:\n" + "\n".join(lines)


@mcp.resource("study://active-recall")
def active_recall_guide() -> str:
    """A practical guide to using active recall while studying."""
    return (
        "Active recall: Read a short section, close your notes, and write or say what you remember. "
        "Check your notes, correct gaps, then try again later without looking."
    )


@mcp.prompt()
def study_plan(topic: str, available_minutes: int = 30) -> str:
    """Create a prompt for planning a focused study session."""
    return (
        f"Create a focused {available_minutes}-minute study plan for: {topic}. "
        "Include a learning goal, timed study blocks, a short break, and a quick self-test."
    )


@mcp.prompt()
def practice_quiz(topic: str, question_count: int = 5) -> str:
    """Create a short recall quiz for a study topic."""
    return (
        f"Write {question_count} clear practice questions about {topic}. "
        "Ask one question at a time, wait for the learner's answer, and then explain the answer briefly."
    )


@mcp.prompt()
def spaced_review(topic: str, review_day: int = 1) -> str:
    """Suggest a spaced-repetition review for a study topic."""
    return (
        f"Prepare a day {review_day} spaced review for {topic}. "
        "Start with a few recall questions, revisit only weak points, and end with one application question."
    )


if __name__ == "__main__":
    mcp.run()

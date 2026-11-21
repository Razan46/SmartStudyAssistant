"""Rule-based routing and specialist agents for study-assistant requests."""

import re

from .mcp_client import mcp_client


class AgentRequestError(ValueError):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def _text_from_tool_result(result):
    if isinstance(result, dict):
        if "result" in result:
            return result["result"]
        return result
    if isinstance(result, list):
        text_items = [item.get("text", "") for item in result if item.get("type") == "text"]
        return "\n".join(text_items) if text_items else result
    return result


def _prompt_text(prompt):
    messages = prompt.get("messages", [])
    parts = []
    for message in messages:
        content = message.get("content", {})
        if content.get("type") == "text":
            parts.append(content.get("text", ""))
    return "\n".join(parts)


class StudyTaskAgent:
    """Uses MCP task tools to add, list, and complete study tasks."""

    def handle(self, action, message, parameters):
        if action == "add_task":
            task = parameters.get("task") or self._after_prefix(message, "add study task", "add task")
            if not task.strip():
                raise AgentRequestError("Provide a study task in parameters.task or message.")
            result = _text_from_tool_result(mcp_client.call_tool("add_task", {"task": task.strip()}))
            if isinstance(result, str) and result == "Task cannot be empty.":
                raise AgentRequestError(result)
            return {"reply": result, "action": action}

        if action == "list_tasks":
            tasks = _text_from_tool_result(mcp_client.call_tool("list_tasks"))
            return {"reply": f"You have {len(tasks)} study task(s).", "tasks": tasks, "action": action}

        task_id = parameters.get("task_id") or self._trailing_id(message)
        if task_id is None:
            raise AgentRequestError("Provide the task ID in parameters.task_id or message.")
        result = _text_from_tool_result(
            mcp_client.call_tool("mark_task_completed", {"task_id": task_id})
        )
        if isinstance(result, str) and result.startswith("No task found"):
            raise AgentRequestError(result, status_code=404)
        return {"reply": result, "action": action}

    @staticmethod
    def _after_prefix(message, *prefixes):
        for prefix in prefixes:
            match = re.match(rf"\s*{re.escape(prefix)}\s*[:\-]?\s*", message, re.IGNORECASE)
            if match:
                return message[match.end():].strip()
        return ""

    @staticmethod
    def _trailing_id(message):
        match = re.search(r"(\d+)\s*$", message)
        return int(match.group(1)) if match else None


class StudyPlanningAgent:
    """Uses the MCP study_plan prompt to prepare a focused session prompt."""

    def handle(self, message, parameters):
        topic = parameters.get("topic") or self._topic_from_message(message)
        if not topic:
            raise AgentRequestError("Provide the study topic in parameters.topic or message.")
        minutes = parameters.get("available_minutes", 30)
        prompt = mcp_client.get_prompt(
            "study_plan", {"topic": topic, "available_minutes": str(minutes)}
        )
        return {"reply": _prompt_text(prompt), "topic": topic, "action": "study_plan"}

    @staticmethod
    def _topic_from_message(message):
        match = re.match(r"\s*(?:study\s+plan\s+for|plan(?:\s+a\s+study\s+session)?\s+for)\s+(.+)", message, re.IGNORECASE)
        return match.group(1).strip() if match else ""


class StudyGuidanceAgent:
    """Reads the MCP study guide resource for study-strategy requests."""

    def handle(self, message, parameters):
        contents = mcp_client.read_resource("study://guide")
        text = "\n".join(item.get("text", "") for item in contents if item.get("text"))
        return {"reply": text, "action": "study_guide"}


class SupervisorAgent:
    """Routes study requests to one of three focused specialists using rules."""

    def __init__(self):
        self.task_agent = StudyTaskAgent()
        self.planning_agent = StudyPlanningAgent()
        self.guidance_agent = StudyGuidanceAgent()

    def handle(self, message, parameters=None):
        parameters = parameters or {}
        action = parameters.get("action") or self._infer_action(message)

        if action in {"add_task", "list_tasks", "complete_task"}:
            return self.task_agent.handle(action, message, parameters)
        if action == "study_plan":
            return self.planning_agent.handle(message, parameters)
        if action == "study_guide":
            return self.guidance_agent.handle(message, parameters)
        raise AgentRequestError(f"Unsupported study action: {action}")

    @staticmethod
    def _infer_action(message):
        normalized = message.strip().lower()
        if normalized.startswith(("add task", "add study task")):
            return "add_task"
        if "complete task" in normalized or "mark task" in normalized:
            return "complete_task"
        if "list task" in normalized or "show task" in normalized:
            return "list_tasks"
        if "study plan" in normalized or normalized.startswith("plan "):
            return "study_plan"
        return "study_guide"


supervisor_agent = SupervisorAgent()

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(ALLOWED_HOSTS=["testserver"])
class MCPChatIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.temp_path = Path(cls.temp_dir.name)
        cls.server_path = cls.temp_path / "server.py"
        shutil.copy2(Path(settings.BASE_DIR) / "server.py", cls.server_path)
        (cls.temp_path / "tasks.json").write_text(
            json.dumps([{"id": 70, "task": "Initial study item", "completed": False}]),
            encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.server_path_patch = patch("chatbot.mcp_client.SERVER_PATH", self.server_path)
        self.server_path_patch.start()
        self.client = APIClient()

    def tearDown(self):
        self.server_path_patch.stop()

    def test_post_lists_study_tasks_through_mcp(self):
        response = self.client.post(
            "/api/chat/", {"message": "list tasks"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tasks"][0]["id"], 70)
        self.assertEqual(response.data["tasks"][0]["task"], "Initial study item")

    def test_add_and_complete_task_persist_in_temporary_storage(self):
        add_response = self.client.post(
            "/api/chat/",
            {
                "message": "Add a study task",
                "parameters": {"action": "add_task", "task": "Review geometry"},
            },
            format="json",
        )

        self.assertEqual(add_response.status_code, 200)
        self.assertIn("Task 71 added successfully", add_response.data["reply"])
        tasks_path = self.temp_path / "tasks.json"
        saved_tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_tasks[-1], {"id": 71, "task": "Review geometry", "completed": False})

        complete_response = self.client.post(
            "/api/chat/",
            {
                "message": "Mark task complete",
                "parameters": {"action": "complete_task", "task_id": 71},
            },
            format="json",
        )

        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(json.loads(tasks_path.read_text(encoding="utf-8"))[-1]["completed"], True)

    def test_post_returns_study_guidance_from_mcp_resource(self):
        response = self.client.post(
            "/api/chat/", {"message": "Give me study guidance"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("active recall", response.data["reply"])

    def test_post_returns_study_plan_from_mcp_prompt(self):
        response = self.client.post(
            "/api/chat/",
            {
                "message": "Plan my study session",
                "parameters": {
                    "action": "study_plan",
                    "topic": "biology",
                    "available_minutes": 25,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("25-minute study plan for: biology", response.data["reply"])

    def test_capabilities_endpoint_lists_required_mcp_capabilities(self):
        response = self.client.get("/api/mcp/capabilities/")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["tools"]), 3)
        self.assertGreaterEqual(len(response.data["resources"]), 3)
        self.assertGreaterEqual(len(response.data["prompts"]), 3)

    def test_missing_message_and_invalid_fields_return_bad_request(self):
        missing_message = self.client.post("/api/chat/", {}, format="json")
        invalid_parameters = self.client.post(
            "/api/chat/",
            {"message": "make a plan", "parameters": {"available_minutes": 0}},
            format="json",
        )
        invalid_json = self.client.generic(
            "POST", "/api/chat/", data=b'{"message":', content_type="application/json"
        )

        self.assertEqual(missing_message.status_code, 400)
        self.assertEqual(invalid_parameters.status_code, 400)
        self.assertEqual(invalid_json.status_code, 400)

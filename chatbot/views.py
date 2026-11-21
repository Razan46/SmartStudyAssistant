from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .agents import AgentRequestError, supervisor_agent
from .mcp_client import MCPClientError, mcp_client
from .serializers import ChatRequestSerializer


class ChatView(APIView):
    parser_classes = [JSONParser]
    renderer_classes = [JSONRenderer]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data["message"].strip()
        parameters = serializer.validated_data.get("parameters", {})
        try:
            return Response(supervisor_agent.handle(message, parameters))
        except AgentRequestError as exc:
            return Response({"error": str(exc)}, status=exc.status_code)
        except MCPClientError as exc:
            return Response({"error": str(exc)}, status=502)


class MCPCapabilitiesView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        try:
            return Response(mcp_client.list_capabilities())
        except MCPClientError as exc:
            return Response({"error": str(exc)}, status=502)

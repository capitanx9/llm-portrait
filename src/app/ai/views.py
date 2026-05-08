from django.conf import settings
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from loguru import logger
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .graph import run_graph
from .serializers import ProcessRequestSerializer, ProcessResponseSerializer


class AIProcessView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessRequestSerializer

    @extend_schema(
        request=ProcessRequestSerializer,
        responses={
            200: ProcessResponseSerializer,
            400: inline_serializer(
                name="AIProcessError400",
                fields={"detail": serializers.CharField()},
            ),
            429: inline_serializer(
                name="AIProcessError429",
                fields={"detail": serializers.CharField()},
            ),
            503: inline_serializer(
                name="AIProcessError503",
                fields={"detail": serializers.CharField()},
            ),
        },
        examples=[
            OpenApiExample(
                "Translate ru → en",
                value={
                    "action": "translate",
                    "message": "Привет, как дела?",
                    "target_language": "en",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Summarize a short conversation",
                value={
                    "action": "summarize",
                    "conversation": [
                        {"role": "user", "content": "morning everyone"},
                        {"role": "user", "content": "PR is up, take a look"},
                        {"role": "user", "content": "rebased onto main, all green"},
                    ],
                },
                request_only=True,
            ),
        ],
    )
    @method_decorator(
        ratelimit(key="user", rate=settings.LLM_RATE_LIMIT, method="POST", block=True)
    )
    def post(self, request: Request) -> Response:
        ser = self.serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)

        action = ser.validated_data["action"]
        logger.info("ai_process_start", user=request.user.id, action=action)
        result = run_graph(dict(ser.validated_data))

        if result.get("error"):
            logger.warning(
                "ai_process_failed",
                node=result.get("failed_node"),
                error=result["error"],
            )
            return Response(
                {"detail": result["error"]},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        payload: dict = {
            "action": action,
            "source_language": result.get("source_language", "en"),
        }
        if "translation" in result:
            payload["translation"] = result["translation"]
        if "summary" in result:
            payload["summary"] = result["summary"]
        return Response(payload, status=status.HTTP_200_OK)

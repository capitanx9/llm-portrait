from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from app.users.management.commands.seed_users import DEMO_PASSWORD, DEMO_USERS
from app.users.models import User

from .serializers import LogoutSerializer, RegisterSerializer, UserSerializer

# Single source of truth for the demo username we surface in Swagger examples.
# Aligned with the Bruno collection (which also uses oleksa/pass1234) so a
# reviewer copy-pasting between the two never has to remap credentials.
_DEMO_USERNAME = DEMO_USERS[0][0]


@extend_schema(
    examples=[
        OpenApiExample(
            f"Login as {_DEMO_USERNAME}",
            value={"username": _DEMO_USERNAME, "password": DEMO_PASSWORD},
            request_only=True,
        ),
    ],
)
class LoginView(TokenObtainPairView):
    """Subclassed only to attach a Swagger example. Behaviour unchanged."""


@extend_schema(
    examples=[
        OpenApiExample(
            "New user",
            value={
                "username": "newcomer",
                "email": "newcomer@example.com",
                "password": DEMO_PASSWORD,
            },
            request_only=True,
        ),
    ],
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes: list = []


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self) -> User:
        return self.request.user


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(
        request=LogoutSerializer,
        responses={
            205: OpenApiResponse(description="Refresh token blacklisted."),
            400: inline_serializer(
                name="LogoutError400",
                fields={"detail": serializers.CharField()},
            ),
        },
        examples=[
            OpenApiExample(
                "Logout",
                value={"refresh": "<paste the refresh token from /api/auth/login/>"},
                request_only=True,
            ),
        ],
    )
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)

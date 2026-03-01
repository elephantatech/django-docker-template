from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import IsAdmin, IsAdminOrOperator
from .serializers import (
    GroupSerializer,
    MeSerializer,
    PasswordChangeSerializer,
    UserCreateSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        if self.action == "me":
            return MeSerializer
        if self.action == "change_password":
            return PasswordChangeSerializer
        return UserListSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAdmin()]
        if self.action in ("list", "retrieve", "update", "partial_update"):
            return [IsAdminOrOperator()]
        if self.action == "destroy":
            return [IsAdmin()]
        if self.action in ("me", "change_password"):
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        user = request.user
        if request.method == "GET":
            serializer = MeSerializer(user)
            return Response(serializer.data)

        # PATCH — ReadOnly users can only change password via change_password
        is_readonly = user.groups.filter(name="ReadOnly").exists()
        is_admin_or_operator = user.groups.filter(name__in=["Admin", "Operator"]).exists()

        if is_readonly and not is_admin_or_operator:
            # ReadOnly users cannot update profile fields via /me/
            return Response(
                {"detail": "ReadOnly users can only change password via /change-password/."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MeSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAdmin()]
        if self.action in ("update", "partial_update"):
            return [IsAdminOrOperator()]
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        user = request.user
        is_admin_or_operator = user.groups.filter(name__in=["Admin", "Operator"]).exists()
        queryset = Group.objects.all() if is_admin_or_operator else user.groups.all()

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

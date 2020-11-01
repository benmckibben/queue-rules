from django.db import IntegrityError
from django.contrib.auth import logout
from rest_framework.exceptions import ValidationError
from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from data.exceptions import BadSpotifyTrackID
from data.models import Rule

from .permissions import IsOwner
from .serializers import RuleSerializer
from .service_checks import run_checks
from .service_checks import ServiceStatus as StatusEnum


class RuleList(generics.ListAPIView):
    serializer_class = RuleSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Rule.objects.filter(owner=self.request.user).order_by("-created")


class RuleDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rule.objects.all()
    serializer_class = RuleSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwner)

    def perform_update(self, serializer):
        try:
            serializer.save()
        except BadSpotifyTrackID as e:
            raise ValidationError(e.message)


class CreateRule(generics.CreateAPIView):
    serializer_class = RuleSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        try:
            serializer.save(owner=self.request.user)
        except BadSpotifyTrackID as e:
            raise ValidationError(e.message)
        except IntegrityError:
            raise ValidationError("Looks like you already have a rule for that song.")


class ServiceStatus(APIView):
    # Intentionally don't have any permissions - this should be publicly available.

    def get(self, request, format=None):
        service_status, check_info = run_checks()

        if service_status == StatusEnum.OK:
            return Response({"status": "OK", "info": check_info}, 200)
        elif service_status == StatusEnum.WARNING:
            return Response({"status": "WARNING", "info": check_info}, 200)
        elif service_status == StatusEnum.CRITICAL:
            return Response({"status": "CRITICAL", "info": check_info}, 503)

        raise ValueError(f"Invalid service status: {service_status}")


class Logout(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        logout(request)
        return Response()


class DeleteAccount(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request):
        user = request.user
        logout(request)
        user.delete()

        return Response()

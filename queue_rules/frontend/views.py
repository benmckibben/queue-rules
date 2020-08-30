from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return render(
            request,
            "frontend/home.html",
            context={"date_joined": request.user.date_joined},
        )

    return render(request, "frontend/login.html")

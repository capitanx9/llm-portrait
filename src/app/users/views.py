from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def landing(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("users:portrait")
    return render(request, "users/landing.html")


@login_required
def portrait_stub(request: HttpRequest) -> HttpResponse:
    return render(request, "users/portrait_stub.html")

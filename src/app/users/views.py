from typing import cast

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_POST

from .forms import UserProfileForm
from .models import User, UserFriends, UserProfile


def landing(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("users:portrait")
    return render(request, "users/landing.html")


class PortraitView(LoginRequiredMixin, View):
    template_name = "users/portrait.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        user = cast(User, request.user)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile_form = UserProfileForm(instance=profile)
        return render(request, self.template_name, self._context(user, profile_form))

    def post(self, request: HttpRequest) -> HttpResponse:
        user = cast(User, request.user)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile_form = UserProfileForm(request.POST, instance=profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Профиль сохранён.")
            return redirect("users:portrait")
        return render(request, self.template_name, self._context(user, profile_form))

    def _context(self, user: User, profile_form: UserProfileForm) -> dict:
        user_model = get_user_model()
        friend_ids = set(UserFriends.objects.filter(user=user).values_list("friend_id", flat=True))
        people = (
            user_model.objects.exclude(pk=user.pk)
            .filter(is_staff=False, is_superuser=False)
            .select_related("profile")
            .order_by("username")
        )
        rows = []
        for person in people:
            friendship_pk = None
            if person.pk in friend_ids:
                friendship_pk = UserFriends.objects.get(user=user, friend=person).pk
            rows.append(
                {
                    "user": person,
                    "is_friend": person.pk in friend_ids,
                    "friendship_pk": friendship_pk,
                }
            )
        return {
            "profile_form": profile_form,
            "people": rows,
        }


@login_required
@require_POST
def friend_add(request: HttpRequest, user_id: int) -> HttpResponseRedirect:
    user = cast(User, request.user)
    target = get_object_or_404(User, pk=user_id)

    if target == user:
        messages.error(request, "Нельзя добавить самого себя.")
    elif UserFriends.objects.filter(user=user, friend=target).exists():
        messages.error(request, "Этот пользователь уже у вас в друзьях.")
    else:
        UserFriends.objects.create(user=user, friend=target)
        messages.success(request, f"{target.username} добавлен в друзья.")

    return redirect(reverse("users:portrait"))


@login_required
@require_POST
def friend_remove(request: HttpRequest, pk: int) -> HttpResponseRedirect:
    user = cast(User, request.user)
    friendship = get_object_or_404(UserFriends, pk=pk, user=user)
    friendship.delete()
    messages.success(request, "Друг удалён.")
    return redirect(reverse("users:portrait"))

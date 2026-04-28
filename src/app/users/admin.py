from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, UserFriends, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ("username", "email", "is_staff", "date_joined")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "arcana", "element", "location", "updated_at")
    list_filter = ("arcana", "element")
    search_fields = ("user__username", "user__email", "location")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserFriends)
class UserFriendsAdmin(admin.ModelAdmin):
    list_display = ("user", "friend", "created_at")
    search_fields = ("user__username", "friend__username")
    autocomplete_fields = ("user", "friend")

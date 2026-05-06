from django.contrib import admin

from .models import Message, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("room", "sender", "created_at")
    list_filter = ("room",)
    search_fields = ("text", "sender__username", "room__name")
    readonly_fields = ("created_at",)

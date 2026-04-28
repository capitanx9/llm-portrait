from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import User, UserFriends, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=UserFriends)
def create_reverse_friendship(sender, instance, created, **kwargs):
    if not created:
        return
    UserFriends.objects.get_or_create(user=instance.friend, friend=instance.user)


@receiver(post_delete, sender=UserFriends)
def remove_reverse_friendship(sender, instance, **kwargs):
    UserFriends.objects.filter(user=instance.friend, friend=instance.user).delete()

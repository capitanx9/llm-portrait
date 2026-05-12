from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User
from .tasks import send_welcome_email


@receiver(post_save, sender=User)
def send_welcome_on_create(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.email:
        transaction.on_commit(lambda: send_welcome_email.delay(instance.pk))

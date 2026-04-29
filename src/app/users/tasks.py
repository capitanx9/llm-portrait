from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail


@shared_task
def send_welcome_email(user_id: int) -> None:
    user_model = get_user_model()
    user = user_model.objects.get(pk=user_id)
    send_mail(
        subject="Добро пожаловать в LLM Portrait!",
        message=(
            f"Привет, {user.username}!\n\n"
            "Спасибо за регистрацию. Заходите на портрет — заполните таро-поля,\n"
            "и наш ИИ сгенерирует для вас персональный портрет.\n\n"
            "—\nLLM Portrait"
        ),
        from_email=None,
        recipient_list=[user.email],
    )


@shared_task
def send_email_async(
    subject: str, body: str, from_email: str | None, recipient_list: list[str]
) -> None:
    send_mail(subject, body, from_email, recipient_list)

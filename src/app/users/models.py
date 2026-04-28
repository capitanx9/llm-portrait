from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models

# ==============================================================================
# Choices
# ==============================================================================

ARCANA_CHOICES = [
    ("fool", "Шут"),
    ("magician", "Маг"),
    ("priestess", "Жрица"),
    ("empress", "Императрица"),
    ("emperor", "Император"),
    ("hierophant", "Иерофант"),
    ("lovers", "Влюблённые"),
    ("chariot", "Колесница"),
    ("strength", "Сила"),
    ("hermit", "Отшельник"),
    ("wheel", "Колесо Фортуны"),
    ("justice", "Справедливость"),
    ("hanged", "Повешенный"),
    ("death", "Смерть"),
    ("temperance", "Умеренность"),
    ("devil", "Дьявол"),
    ("tower", "Башня"),
    ("star", "Звезда"),
    ("moon", "Луна"),
    ("sun", "Солнце"),
    ("judgement", "Суд"),
    ("world", "Мир"),
]

ELEMENT_CHOICES = [
    ("fire", "Огонь"),
    ("water", "Вода"),
    ("air", "Воздух"),
    ("earth", "Земля"),
]


# ==============================================================================
# User
# ==============================================================================


class User(AbstractUser):
    email = models.EmailField(unique=True)


# ==============================================================================
# UserProfile
# ==============================================================================


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    age = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(13), MaxValueValidator(120)],
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        validators=[MinLengthValidator(2)],
    )
    arcana = models.CharField(max_length=20, choices=ARCANA_CHOICES, blank=True)
    shadow = models.CharField(max_length=500, blank=True, validators=[MinLengthValidator(10)])
    quest = models.CharField(max_length=500, blank=True, validators=[MinLengthValidator(10)])
    curse = models.CharField(max_length=500, blank=True, validators=[MinLengthValidator(10)])

    element = models.CharField(max_length=10, choices=ELEMENT_CHOICES, blank=True)
    totem = models.CharField(max_length=500, blank=True, validators=[MinLengthValidator(10)])
    forbidden_magic = models.CharField(
        max_length=500, blank=True, validators=[MinLengthValidator(10)]
    )

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        arcana = self.get_arcana_display() or "—"
        return f"{self.user.username} ({arcana})"


# ==============================================================================
# UserFriends
# ==============================================================================


class UserFriends(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friendships_initiated")
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friendships_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "friend")]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(user=models.F("friend")),
                name="users_userfriends_no_self_friendship",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} ↔ {self.friend.username}"

from django import forms

from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "age",
            "location",
            "arcana",
            "element",
            "shadow",
            "quest",
            "curse",
            "totem",
            "forbidden_magic",
        ]
        widgets = {
            "age": forms.NumberInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "arcana": forms.Select(attrs={"class": "form-select"}),
            "element": forms.Select(attrs={"class": "form-select"}),
            "shadow": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "quest": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "curse": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "totem": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "forbidden_magic": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "age": "Возраст",
            "location": "Локация",
            "arcana": "Аркана",
            "element": "Стихия",
            "shadow": "Тень",
            "quest": "Путь",
            "curse": "Проклятие",
            "totem": "Тотем",
            "forbidden_magic": "Запретная магия",
        }
        help_texts = {
            "age": "Сколько вам лет.",
            "location": "Город или страна, где вы сейчас живёте.",
            "arcana": (
                "Ваш главный архетип из 22 Старших Арканов Таро. "
                "Маг — про действие и силу воли, Жрица — про интуицию и тайное знание, "
                "Шут — про свободу и начало пути. Выберите ту, что отзывается."
            ),
            "element": (
                "Ваша стихия. Огонь — страсть и движение. Вода — чувства и память. "
                "Воздух — мысли и общение. Земля — тело и устойчивость."
            ),
            "shadow": (
                "Ваша Тень — то, что вы скрываете даже от себя. "
                "Какая ваша черта чаще всего вам мешает? "
                "Пример: «склонность откладывать важное до последнего»."
            ),
            "quest": (
                "Ваш Путь — главная задача этой жизни, как вы её видите. "
                "Пример: «научиться отстаивать границы и при этом не закрываться от людей»."
            ),
            "curse": (
                "Ваше Проклятие — повторяющийся паттерн, который вас догоняет. "
                "Пример: «начинаю много проектов, но почти ни один не довожу до конца»."
            ),
            "totem": (
                "Ваш Тотем — образ-животное или объект, в котором вы узнаёте себя. "
                "Пример: «волк-одиночка в зимнем лесу» или «старая печатная машинка»."
            ),
            "forbidden_magic": (
                "Запретная магия — навык или сила, которой вы боитесь пользоваться. "
                "Пример: «умею читать людей насквозь, но избегаю этого»."
            ),
        }

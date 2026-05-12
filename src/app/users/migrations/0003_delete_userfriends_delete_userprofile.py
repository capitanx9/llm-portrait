from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_userprofile_userfriends"),
    ]

    operations = [
        migrations.DeleteModel(name="UserFriends"),
        migrations.DeleteModel(name="UserProfile"),
    ]

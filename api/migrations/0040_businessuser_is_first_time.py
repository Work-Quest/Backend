from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0039_businessuser_bg_color_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessuser",
            name="is_first_time",
            field=models.BooleanField(default=True),
        ),
    ]

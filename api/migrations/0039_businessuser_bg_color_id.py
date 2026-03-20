from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0038_businessuser_selected_character_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessuser",
            name="bg_color_id",
            field=models.PositiveSmallIntegerField(
                default=1,
                validators=[MinValueValidator(1), MaxValueValidator(8)],
            ),
        ),
    ]

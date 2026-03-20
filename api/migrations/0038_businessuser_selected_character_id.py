from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0037_projectendsummary"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessuser",
            name="selected_character_id",
            field=models.PositiveSmallIntegerField(
                default=1,
                validators=[MinValueValidator(1), MaxValueValidator(9)],
            ),
        ),
    ]

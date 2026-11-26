from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DatabaseCacheEntry",
            fields=[
                (
                    "cache_key",
                    models.CharField(max_length=255, primary_key=True, serialize=False),
                ),
                ("value", models.TextField()),
                ("expires", models.DateTimeField(db_index=True)),
            ],
            options={"db_table": "django_cache"},
        ),
    ]
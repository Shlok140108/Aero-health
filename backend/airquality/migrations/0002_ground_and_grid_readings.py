from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("airquality", "0001_initial")]
    operations = [
        migrations.CreateModel(name="GroundReading", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("aqi", models.FloatField(blank=True, null=True)), ("timestamp", models.DateTimeField(db_index=True)),
            ("source", models.CharField(default="CPCB", max_length=30)), ("pollutants", models.JSONField(blank=True, default=dict)),
            ("location", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ground_readings", to="airquality.location")),
        ], options={"ordering": ["-timestamp"]}),
        migrations.AddIndex(model_name="groundreading", index=models.Index(fields=["location", "-timestamp"], name="ground_loc_time_idx")),
        migrations.CreateModel(name="AQIGridPoint", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("lat", models.FloatField()), ("lon", models.FloatField()), ("aqi", models.FloatField()), ("timestamp", models.DateTimeField(db_index=True)),
            ("source", models.CharField(default="satellite_model", max_length=40)), ("model_version", models.CharField(blank=True, max_length=80)),
            ("uncertainty_low", models.FloatField(blank=True, null=True)), ("uncertainty_high", models.FloatField(blank=True, null=True)),
        ]),
        migrations.AddIndex(model_name="aqigridpoint", index=models.Index(fields=["timestamp"], name="aqi_grid_time_idx")),
    ]

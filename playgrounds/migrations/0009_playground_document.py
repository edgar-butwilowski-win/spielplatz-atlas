# Generated manually for SpielplatzAtlas

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('playgrounds', '0008_playground_lv95_coordinate_labels'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlaygroundDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('certificate', 'Zertifikatsdokument'), ('acceptance', 'Abnahmedokument')], max_length=20, verbose_name='Dokumentart')),
                ('mime_type', models.CharField(default='application/pdf', max_length=100, verbose_name='MIME-Type')),
                ('size_bytes', models.PositiveIntegerField(verbose_name='Dateigrösse in Bytes')),
                ('sha256', models.CharField(db_index=True, max_length=64, verbose_name='SHA-256')),
                ('data', models.BinaryField(verbose_name='Dateidaten')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Erstellt am')),
                ('playground', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='playgrounds.playground', verbose_name='Spielplatz')),
            ],
            options={
                'verbose_name': 'Spielplatz-Dokument',
                'verbose_name_plural': 'Spielplatz-Dokumente',
                'ordering': ['document_type', 'id'],
            },
        ),
    ]

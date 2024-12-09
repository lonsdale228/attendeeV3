# Generated by Django 5.1.2 on 2024-12-08 22:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bots', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaBlob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.CharField(editable=False, max_length=32, unique=True)),
                ('blob', models.BinaryField()),
                ('content_type', models.CharField(choices=[('audio/mp3', 'MP3 Audio'), ('image/png', 'PNG Image')], max_length=255)),
                ('checksum', models.CharField(editable=False, max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('duration_ms', models.IntegerField()),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='media_blobs', to='bots.project')),
            ],
        ),
        migrations.CreateModel(
            name='BotMediaRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_type', models.IntegerField(choices=[(1, 'Image'), (2, 'Audio')])),
                ('state', models.IntegerField(choices=[(1, 'Enqueued'), (2, 'Playing'), (3, 'Dropped'), (4, 'Finished'), (5, 'Failed to Play')], default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media_requests', to='bots.bot')),
                ('media_blob', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bot_media_requests', to='bots.mediablob')),
            ],
        ),
        migrations.AddConstraint(
            model_name='mediablob',
            constraint=models.UniqueConstraint(fields=('project', 'checksum'), name='unique_project_blob'),
        ),
        migrations.AddConstraint(
            model_name='botmediarequest',
            constraint=models.UniqueConstraint(condition=models.Q(('state', 2)), fields=('bot', 'media_type'), name='unique_playing_media_request_per_bot_and_type'),
        ),
    ]

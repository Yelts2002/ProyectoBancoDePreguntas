# Generated by Django 5.1.5 on 2025-05-04 21:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Preguntas', '0010_curso_universidad_alter_tema_curso_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='curso',
            name='universidad',
        ),
        migrations.AddField(
            model_name='universidad',
            name='cursos',
            field=models.ManyToManyField(related_name='universidades', to='Preguntas.curso'),
        ),
        migrations.AlterField(
            model_name='curso',
            name='nombre',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='tema',
            name='curso',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='temas', to='Preguntas.curso'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='tema',
            name='nombre',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='universidad',
            name='nombre',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]

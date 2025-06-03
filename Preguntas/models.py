from django.db import models
from django.core.validators import FileExtensionValidator 
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta

class Curso(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Tema(models.Model):
    nombre = models.CharField(max_length=100)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='temas')

    def __str__(self):
        return f"{self.nombre} ({self.curso.nombre})"


class Universidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    cursos = models.ManyToManyField(Curso, related_name='universidades')

    def __str__(self):
        return self.nombre
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)  # Campo para activar/desactivar
    ROLE_CHOICES = [
        ('supervisor', 'Supervisor'),
        ('admin', 'Admin'),
        ('user', 'User '),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User )
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User )
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save() 

@receiver(post_save, sender=UserProfile)
def update_user_status(sender, instance, **kwargs):
    if instance.user.is_active != instance.is_active:
        User.objects.filter(id=instance.user.id).update(is_active=instance.is_active)

class Pregunta(models.Model):
    RESPUESTA_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
    ]

    universidad = models.ForeignKey(Universidad, on_delete=models.SET_NULL, null=True)
    curso = models.ForeignKey(Curso, on_delete=models.SET_NULL, null=True)
    tema = models.ForeignKey(Tema, on_delete=models.SET_NULL, null=True)

    nivel = models.PositiveSmallIntegerField(default=1, help_text="Nivel de dificultad (por ejemplo: 1, 2, 3...)")
    respuesta = models.CharField(
        max_length=1,
        choices=RESPUESTA_CHOICES,
        default='A',
        help_text="Respuesta correcta (A, B, C, D o E)"
    )

    nombre = models.CharField(max_length=300, blank=True)
    contenido = models.FileField(
        upload_to='preguntas/',
        validators=[FileExtensionValidator(allowed_extensions=['doc', 'docx'])],
        help_text="Suba un archivo .doc o .docx con la pregunta"
    )

    usuario = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        # Generar nombre automático si no se ha asignado
        if not self.nombre and self.universidad and self.curso and self.tema:
            count = Pregunta.objects.filter(
                universidad=self.universidad,
                curso=self.curso,
                tema=self.tema,
                nivel=self.nivel
            ).count() + 1

            self.nombre = f"{self.universidad.id}{self.curso.id}{self.tema.id}{self.nivel}{count}"

        if not self.id:
            self.fecha_creacion = timezone.now()

        super().save(*args, **kwargs)
        
    tiene_solucion = models.BooleanField(
        default=False,
        help_text="Indica si la pregunta tiene solución"
    )
    @property
    def usada(self):
        return ExamenPregunta.objects.filter(pregunta=self).exists()
    @property
    def fecha_expiracion(self):
        return self.fecha_creacion + timedelta(days=1)

    def __str__(self):
        return self.nombre

class Examen(models.Model):
    nombre = models.CharField(max_length=200)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.nombre

class ExamenPregunta(models.Model):
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE, related_name='examen_preguntas')
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='examen_preguntas')

    class Meta:
        unique_together = ('examen', 'pregunta')

    def __str__(self):
        return f"{self.examen.nombre} - {self.pregunta.nombre}"
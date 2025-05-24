import csv
from django.core.paginator import Paginator
from ..models import Universidad, Curso, Tema, Pregunta, UserProfile
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from .auth_views import exclude_supervisor
from django.views.decorators.http import require_POST


@exclude_supervisor
@staff_member_required
def admin_dashboard(request):
    # Filtros
    filtros = {}
    for campo in ['tema', 'universidad', 'curso']:
        valor = request.GET.get(campo)
        if valor:
            filtros[campo + '__id'] = valor
    
    # Preguntas filtradas y ordenadas
    preguntas_qs = Pregunta.objects.filter(**filtros).order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(preguntas_qs, 20)
    page_number = request.GET.get('page')
    preguntas_recientes = paginator.get_page(page_number)
    
    # Estadísticas
    preguntas_por_usuario = {}
    for user in User.objects.all():
        preguntas_count = Pregunta.objects.filter(usuario__user=user).count()
        preguntas_por_usuario[user.username] = {
            'cantidad': preguntas_count,
            'is_active': user.userprofile.is_active,
            'role': user.userprofile.role,
        }
    
    context = {
        'universidades_count': Universidad.objects.count(),
        'cursos_count': Curso.objects.count(),
        'temas_count': Tema.objects.count(),
        'preguntas_count': Pregunta.objects.count(),
        'preguntas_por_usuario': preguntas_por_usuario,
        'roles': UserProfile.ROLE_CHOICES,
        'preguntas_recientes': preguntas_recientes,
        'temas': Tema.objects.all(),
        'universidades': Universidad.objects.all(),
        'cursos': Curso.objects.all(),
    }
    
    # Agregar los valores de filtro al contexto
    for campo in ['tema', 'universidad', 'curso']:
        context[f'{campo}_filter'] = request.GET.get(campo)
    
    return render(request, 'Preguntas/admin_dashboard.html', context)


@login_required
@staff_member_required
@require_POST
def change_user_role(request, username):
    user = get_object_or_404(User, username=username)
    user_profile = get_object_or_404(UserProfile, user=user)

    new_role = request.POST.get('role')
    if new_role in dict(UserProfile.ROLE_CHOICES).keys():
        user_profile.role = new_role
        user_profile.save()
        messages.success(request, f"Cargo de {user.username} actualizado a {dict(UserProfile.ROLE_CHOICES)[new_role]}.")
    else:
        messages.error(request, "No se seleccionó un cargo válido.")

    return redirect('admin-dashboard')

@login_required
@staff_member_required
def toggle_user_status(request, username):
    user = get_object_or_404(User, username=username)
    user_profile = get_object_or_404(UserProfile, user=user)

    # Cambiar el estado de is_active
    user_profile.is_active = not user_profile.is_active
    user_profile.save()

    # Mensaje de éxito
    if user_profile.is_active:
        messages.success(request, f'La cuenta de {user.username} ha sido activada.')
    else:
        messages.warning(request, f'La cuenta de {user.username} ha sido desactivada.')

    # Redirigir de vuelta al dashboard
    return redirect('admin-dashboard')  # Asegúrate de que este nombre coincida con tu URL



@exclude_supervisor
@login_required
def export_preguntas_recientes(request):
    """
    Exporta en formato CSV las preguntas recientes, optimizando las consultas y el manejo del archivo.
    """
    preguntas = Pregunta.objects.select_related('usuario__user', 'universidad', 'curso', 'tema').order_by('-fecha_creacion')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="preguntas_recientes.csv"'

    # Agregar BOM para UTF-8 para compatibilidad con Excel
    response.write(u'﻿'.encode('utf8'))

    fieldnames = ['Usuario', 'Universidad', 'Curso', 'Tema', 'Nivel', 'Fecha de Creación']
    writer = csv.DictWriter(response, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    writer.writeheader()
    writer.writerows({
        'Usuario': pregunta.usuario.user.username if pregunta.usuario else 'Desconocido',
        'Universidad': pregunta.universidad.nombre,
        'Curso': pregunta.curso.nombre,
        'Tema': pregunta.tema.nombre,
        'Nivel': pregunta.nivel,
        'Fecha de Creación': pregunta.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S"),
    } for pregunta in preguntas)

    return response
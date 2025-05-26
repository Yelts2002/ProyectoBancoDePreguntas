from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages

from ..models import Examen, Pregunta, ExamenPregunta, Tema, Universidad, Curso
from .pregunta_views import combinar_documentos
from django.db.models import OuterRef, Exists, Subquery, Max

@staff_member_required
def generar_examen(request):
    # Obtener filtros desde GET
    filtros = {}
    for campo in ['tema', 'universidad', 'curso']:
        valor = request.GET.get(campo)
        if valor:
            filtros[campo + '__id'] = valor

    # Cargar carrito desde sesión
    carrito_ids = request.session.get('carrito', [])
    carrito = Pregunta.objects.filter(id__in=carrito_ids).select_related('universidad', 'curso', 'tema')

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        pregunta_ids = request.POST.getlist('preguntas')

        if 'add_to_cart' in request.POST:
            for pid in pregunta_ids:
                if pid and pid not in carrito_ids:
                    carrito_ids.append(pid)
            request.session['carrito'] = carrito_ids
            return JsonResponse({'success': True}) if is_ajax else redirect('generar_examen')

        elif 'add_preview' in request.POST:
            pid = request.POST.get('pregunta_id')
            if pid and pid not in carrito_ids:
                carrito_ids.append(pid)
            request.session['carrito'] = carrito_ids
            return JsonResponse({'success': True}) if is_ajax else redirect('generar_examen')

        elif 'remove_from_cart' in request.POST:
            for pid in pregunta_ids:
                if pid in carrito_ids:
                    carrito_ids.remove(pid)
            request.session['carrito'] = carrito_ids
            return JsonResponse({'success': True}) if is_ajax else redirect('generar_examen')

        elif 'vaciar_carrito' in request.POST:
            carrito_ids.clear()
            request.session['carrito'] = carrito_ids
            return JsonResponse({'success': True}) if is_ajax else redirect('generar_examen')

        elif 'download' in request.POST:
            preguntas_seleccionadas = Pregunta.objects.filter(id__in=carrito_ids)
            if not preguntas_seleccionadas.exists():
                messages.error(request, "No hay preguntas en el carrito para descargar.")
                return redirect('generar_examen')

            # CREAR EL EXAMEN EN LA BASE DE DATOS
            from datetime import datetime
            examen = Examen.objects.create(
                nombre=f"Examen_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                usuario=request.user.userprofile  # Ajusta según tu modelo de usuario
            )

            # RELACIONAR LAS PREGUNTAS CON EL EXAMEN
            for pregunta in preguntas_seleccionadas:
                ExamenPregunta.objects.create(
                    examen=examen,
                    pregunta=pregunta
                )

            # Generar el archivo para descarga
            buffer = combinar_documentos(preguntas_seleccionadas)
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="examen_{examen.id}.docx"'
            
            request.session['carrito'] = []
            
            return response

        elif 'download_respuestas' in request.POST:
            preguntas_seleccionadas = Pregunta.objects.filter(id__in=carrito_ids)
            if not preguntas_seleccionadas.exists():
                messages.error(request, "No hay preguntas en el carrito para generar las respuestas.")
                return redirect('generar_examen')

            import csv
            from django.utils.encoding import smart_str

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="respuestas_examen.csv"'

            writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['N°', 'Curso', 'Tema', 'Nombre de la Pregunta', 'Respuesta'])

            for i, pregunta in enumerate(preguntas_seleccionadas, start=1):
                writer.writerow([
                    i,
                    smart_str(pregunta.curso.nombre),
                    smart_str(pregunta.tema.nombre),
                    smart_str(pregunta.nombre),
                    smart_str(pregunta.get_respuesta_display())
                ])

            return response

    # MOVER AQUÍ LA CONSULTA DE PREGUNTAS CON ANOTACIONES
    # Para que se ejecute después de cualquier operación POST que pueda cambiar el estado
    
    # Subquery para verificar uso
    subquery = ExamenPregunta.objects.filter(pregunta=OuterRef('pk'))

    # Subquery para obtener la fecha máxima de examen donde se usó la pregunta
    fecha_ultimo_uso_subquery = ExamenPregunta.objects.filter(
        pregunta=OuterRef('pk')
    ).select_related('examen').order_by('-examen__fecha_creacion').values('examen__fecha_creacion')[:1]

    # Aplicar filtro y anotaciones juntas para no perder el filtro
    preguntas = Pregunta.objects.filter(**filtros).annotate(
        usada_flag=Exists(subquery),
        fecha_ultimo_uso=Subquery(fecha_ultimo_uso_subquery)
    )

    # DEBUG TEMPORAL - quitar después de confirmar que funciona
    for p in preguntas:
        print(f"Pregunta {p.id}: usada_flag={p.usada_flag}, fecha_ultimo_uso={p.fecha_ultimo_uso}")
    # FIN DEBUG

    # Recargar carrito actualizado para mostrar en la plantilla
    carrito_preguntas = Pregunta.objects.filter(id__in=carrito_ids)

    # Asignar atributos temporales para la plantilla
    for pregunta in preguntas:
        pregunta.is_usada = pregunta.usada_flag
        # fecha_ultimo_uso ya viene anotada, no hace falta reasignar

    context = {
        'preguntas': preguntas,
        'temas': Tema.objects.all(),
        'universidades': Universidad.objects.all(),
        'cursos': Curso.objects.all(),
        'carrito': carrito_preguntas,
    }

    for campo in ['tema', 'universidad', 'curso']:
        context[f'{campo}_filter'] = request.GET.get(campo)

    return render(request, 'Preguntas/generar_examen.html', context)
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone

from ..models import Examen, Pregunta, ExamenPregunta, Tema, Universidad, Curso
from .pregunta_views import combinar_documentos
from django.db.models import OuterRef, Exists, Subquery

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
            fecha_actual = datetime.now().strftime('%Y-%m-%d')    
            examen = Examen.objects.create(
                nombre=f"Examen_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                usuario=request.user.userprofile
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
            response['Content-Disposition'] = f'attachment; filename="Simulacro {fecha_actual}.docx"'
                        
            return response

        elif 'download_respuestas' in request.POST:
            preguntas_seleccionadas = Pregunta.objects.filter(id__in=carrito_ids)
            if not preguntas_seleccionadas.exists():
                messages.error(request, "No hay preguntas en el carrito para generar las respuestas.")
                return redirect('generar_examen')

            import csv
            from datetime import datetime
            from django.utils.encoding import smart_str
            fecha_actual = datetime.now().strftime('%Y-%m-%d')

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="Alternativas {fecha_actual}.csv"'

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
    
    # Subquery para verificar uso
    subquery = ExamenPregunta.objects.filter(pregunta=OuterRef('pk'))

    # Subquery para obtener la fecha máxima de examen donde se usó la pregunta
    fecha_ultimo_uso_subquery = ExamenPregunta.objects.filter(
        pregunta=OuterRef('pk')
    ).select_related('examen').order_by('-examen__fecha_creacion').values('examen__fecha_creacion')[:1]

    # Aplicar filtro y anotaciones juntas con ordenación
    preguntas = Pregunta.objects.filter(**filtros).annotate(
        usada_flag=Exists(subquery),
        fecha_ultimo_uso=Subquery(fecha_ultimo_uso_subquery)
    ).order_by('-fecha_creacion')  # Ordenar por fecha de creación descendente

    # Paginación - 30 preguntas por página
    paginator = Paginator(preguntas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Asignar atributos temporales para la plantilla
    for pregunta in page_obj.object_list:
        pregunta.is_usada = pregunta.usada_flag

    # Recargar carrito actualizado para mostrar en la plantilla
    carrito_preguntas = Pregunta.objects.filter(id__in=carrito_ids)

    context = {
        'page_obj': page_obj,  # Usar page_obj en lugar de preguntas
        'temas': Tema.objects.all(),
        'universidades': Universidad.objects.all(),
        'cursos': Curso.objects.all(),
        'carrito': carrito_preguntas,
        'tema_filter': request.GET.get('tema'),
        'universidad_filter': request.GET.get('universidad'),
        'curso_filter': request.GET.get('curso'),
        'now': timezone.now(),

    }

    return render(request, 'Preguntas/generar_examen.html', context)
from ..models import Universidad, Tema, Curso, Pregunta
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse

from .pregunta_views import combinar_documentos

@staff_member_required
def generar_examen(request):
    # Filtros
    filtros = {}
    for campo in ['tema', 'universidad', 'curso']:
        valor = request.GET.get(campo)
        if valor:
            filtros[campo + '__id'] = valor

    # Preguntas filtradas
    preguntas = Pregunta.objects.filter(**filtros).order_by('-fecha_creacion')
    carrito = request.session.get('carrito', [])

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Obtener todos los IDs de preguntas
        pregunta_ids = request.POST.getlist('preguntas')  # Cambiado a getlist para obtener múltiples IDs

        # Añadir al carrito
        if 'add_to_cart' in request.POST:
            for pregunta_id in pregunta_ids:
                if pregunta_id and pregunta_id not in carrito:
                    carrito.append(pregunta_id)
            request.session['carrito'] = carrito

            if is_ajax:
                return JsonResponse({'success': True})
            else:
                return redirect('generar_examen')

        # Añadir pregunta desde la vista previa
        elif 'add_preview' in request.POST:
            pregunta_id = request.POST.get('pregunta_id')  # ID de la pregunta desde la vista previa
            if pregunta_id and pregunta_id not in carrito:
                carrito.append(pregunta_id)
            request.session['carrito'] = carrito

            if is_ajax:
                return JsonResponse({'success': True})
            else:
                return redirect('generar_examen')

        # Eliminar del carrito
        elif 'remove_from_cart' in request.POST:
            for pregunta_id in pregunta_ids:
                if pregunta_id in carrito:
                    carrito.remove(pregunta_id)
            request.session['carrito'] = carrito

            if is_ajax:
                return JsonResponse({'success': True})
            else:
                return redirect('generar_examen')

        # Vaciar el carrito
        elif 'vaciar_carrito' in request.POST:
            carrito.clear()  # Vaciar el carrito
            request.session['carrito'] = carrito

            if is_ajax:
                return JsonResponse({'success': True})
            else:
                return redirect('generar_examen')

        # Descargar preguntas del carrito
        elif 'download' in request.POST:
            preguntas_seleccionadas = Pregunta.objects.filter(id__in=carrito)
            if not preguntas_seleccionadas:
                messages.error(request, "No hay preguntas en el carrito para descargar.")
                return redirect('generar_examen')

            buffer = combinar_documentos(preguntas_seleccionadas)
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = 'attachment; filename="examen_generado.docx"'
            return response
        
        
        # Descargar respuestas de las preguntas del carrito 
        elif 'download_respuestas' in request.POST: 
            preguntas_seleccionadas = Pregunta.objects.filter(id__in=carrito) 
            if not preguntas_seleccionadas: 
                messages.error(request, "No hay preguntas en el carrito para generar las respuestas.") 
                return redirect('generar_examen') 

            import csv 
            from django.utils.encoding import smart_str 

            # Crear la respuesta HTTP con tipo CSV 
            response = HttpResponse(content_type='text/csv') 
            response['Content-Disposition'] = 'attachment; filename="respuestas_examen.csv"' 
            
            # Configurar un delimitador específico (punto y coma) que funciona mejor para tablas
            writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            # Encabezados 
            writer.writerow([ 
                'N°', 
                'Curso', 
                'Tema', 
                'Nombre de la Pregunta', 
                'Respuesta' 
            ]) 

            # Datos 
            for i, pregunta in enumerate(preguntas_seleccionadas, start=1): 
                writer.writerow([ 
                    i, 
                    smart_str(pregunta.curso.nombre), 
                    smart_str(pregunta.tema.nombre), 
                    smart_str(pregunta.nombre), 
                    smart_str(pregunta.get_respuesta_display()) 
                ]) 

            return response


    # Obtener preguntas en el carrito
    carrito_preguntas = Pregunta.objects.filter(id__in=carrito)

    # Mostrar formulario
    context = {
        'preguntas': preguntas,
        'temas': Tema.objects.all(),
        'universidades': Universidad.objects.all(),
        'cursos': Curso.objects.all(),
        'carrito': carrito_preguntas,
    }

    # Agregar los valores de filtro al contexto
    for campo in ['tema', 'universidad', 'curso']:
        context[f'{campo}_filter'] = request.GET.get(campo)

    return render(request, 'Preguntas/generar_examen.html', context)
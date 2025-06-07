import os
import tempfile
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from copy import deepcopy 
from ..forms import CargaMasivaPreguntaForm
from ..models import Pregunta, UserProfile
from .auth_views import exclude_supervisor
from contextlib import contextmanager
from django.contrib.admin.views.decorators import staff_member_required

@contextmanager
def temp_docx_file(content_bytes, suffix='.docx'):
    """Context manager para manejo seguro de archivos temporales"""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content_bytes)
            temp_path = temp_file.name
        yield temp_path
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

@login_required
@staff_member_required
@exclude_supervisor
def masivo_pregunta_create(request):
    if request.method == 'POST':
        form = CargaMasivaPreguntaForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, 'Por favor corrija los errores en el formulario.')
            return render(request, 'Preguntas/masivo_pregunta_form.html', {
                'form': form,
                'title': 'Carga Masiva de Preguntas'
            })

        try:
            # Datos del formulario
            data = form.cleaned_data
            universidad = data['universidad']
            curso = data['curso']
            tema = data['tema']
            nivel = data['nivel']
            respuesta_default = data['respuesta_default']
            archivo_word = data['archivo']

            # Leer el archivo una sola vez
            archivo_bytes = archivo_word.read()
            user_profile = UserProfile.objects.get(user=request.user)
            
            # Procesar documento
            with temp_docx_file(archivo_bytes) as temp_path:
                doc = Document(temp_path)
                
                # Separar bloques por el separador '*****'
                all_blocks = []
                current_block = []
                
                for element in doc.element.body:
                    # Buscar texto en el elemento
                    text_elements = element.xpath('.//w:t')
                    text = ''.join(t.text for t in text_elements if t.text).strip()

                    if text == '*****':
                        if current_block:
                            all_blocks.append(current_block)
                            current_block = []
                    else:
                        current_block.append(element)

                if current_block:
                    all_blocks.append(current_block)

            # Contador base para nombres de preguntas
            base_count = Pregunta.objects.filter(
                universidad=universidad,
                curso=curso,
                tema=tema,
                nivel=nivel
            ).count()

            preguntas_creadas = 0
            
            # Procesar cada bloque como pregunta
            for i, block_elements in enumerate(all_blocks, start=1):
                # Crear nuevo documento basado en el original
                with temp_docx_file(archivo_bytes) as temp_path:
                    new_doc = Document(temp_path)
                    body = new_doc._element.body
                    
                    # Limpiar y añadir solo el bloque actual
                    body.clear_content()
                    for element in block_elements:
                        body.append(deepcopy(element))
                    
                    # Aplicar formato consistente
                    for para in new_doc.paragraphs:
                        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        para.paragraph_format.left_indent = Pt(0)
                    
                    # Guardar en memoria
                    buffer = BytesIO()
                    new_doc.save(buffer)
                    buffer.seek(0)

                # Crear la pregunta
                pregunta = Pregunta(
                    universidad=universidad,
                    curso=curso,
                    tema=tema,
                    nivel=nivel,
                    respuesta=respuesta_default,
                    usuario=user_profile,
                    tiene_solucion=False,
                    nombre=f"{universidad.id}{curso.id}{tema.id}{nivel}{base_count + i}"
                )
                pregunta.save()
                
                # Guardar archivo
                filename = f"pregunta_{pregunta.nombre}.docx"
                pregunta.contenido.save(filename, File(buffer))
                preguntas_creadas += 1

            messages.success(request, f'Se crearon {preguntas_creadas} preguntas exitosamente.')
            return redirect('pregunta_list')

        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {str(e)}')
            return render(request, 'Preguntas/masivo_pregunta_form.html', {
                'form': form,
                'title': 'Carga Masiva de Preguntas'
            })

    # GET request
    form = CargaMasivaPreguntaForm()
    return render(request, 'Preguntas/masivo_pregunta_form.html', {
        'form': form,
        'title': 'Carga Masiva de Preguntas'
    })
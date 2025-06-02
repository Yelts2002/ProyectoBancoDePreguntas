from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from io import BytesIO
from docx import Document
import re
from ..forms import CargaMasivaPreguntaForm
from ..models import Pregunta, UserProfile
from django.contrib.admin.views.decorators import staff_member_required
from .auth_views import exclude_supervisor

@login_required
@exclude_supervisor
def masivo_pregunta_create(request):
    if request.method == 'POST':
        form = CargaMasivaPreguntaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Obtener datos del formulario
                universidad = form.cleaned_data['universidad']
                curso = form.cleaned_data['curso']
                tema = form.cleaned_data['tema']
                nivel = form.cleaned_data['nivel']
                respuesta_default = form.cleaned_data['respuesta_default']
                archivo_word = form.cleaned_data['archivo']
                
                # Obtener perfil de usuario
                user_profile = UserProfile.objects.get(user=request.user)
                preguntas_creadas = 0
                
                # Procesar el documento Word
                doc = Document(archivo_word)
                full_text = "\n".join([para.text for para in doc.paragraphs])
                
                # Dividir preguntas por el separador
                preguntas_texto = re.split(r'\*{5,}', full_text)
                preguntas_texto = [p.strip() for p in preguntas_texto if p.strip()]
                
                for pregunta_texto in preguntas_texto:
                    if not pregunta_texto:
                        continue
                    
                    # Crear un nuevo documento para cada pregunta
                    new_doc = Document()
                    for line in pregunta_texto.split('\n'):
                        if line.strip():
                            new_doc.add_paragraph(line.strip())
                    
                    # Guardar en buffer
                    buffer = BytesIO()
                    new_doc.save(buffer)
                    buffer.seek(0)
                    
                    # Crear la pregunta en la base de datos
                    pregunta = Pregunta(
                        universidad=universidad,
                        curso=curso,
                        tema=tema,
                        nivel=nivel,
                        respuesta=respuesta_default,
                        usuario=user_profile,
                        tiene_solucion=False
                    )
                    
                    # Generar nombre automático
                    count = Pregunta.objects.filter(
                        universidad=universidad,
                        curso=curso,
                        tema=tema,
                        nivel=nivel
                    ).count() + 1
                    
                    pregunta.nombre = f"{universidad.id}{curso.id}{tema.id}{nivel}{count}"
                    pregunta.save()
                    
                    # Guardar el archivo individual
                    filename = f"pregunta_{pregunta.nombre}.docx"
                    pregunta.contenido.save(filename, File(buffer))
                    pregunta.save()
                    
                    preguntas_creadas += 1
                    buffer.close()
                
                messages.success(request, f'Se crearon {preguntas_creadas} preguntas exitosamente.')
                return redirect('pregunta_list')
                
            except Exception as e:
                messages.error(request, f'Error al procesar el archivo: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = CargaMasivaPreguntaForm()
    
    return render(request, 'Preguntas/masivo_pregunta_form.html', {
        'form': form,
        'title': 'Carga Masiva de Preguntas'
    })
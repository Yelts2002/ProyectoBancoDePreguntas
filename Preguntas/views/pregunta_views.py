# Importaciones relativas del proyecto
from ..models import Universidad, Tema, Curso, Pregunta, UserProfile
from ..forms import Pregunta, FiltroPreguntaForm, PreguntaForm

# Django - shortcuts y decoradores
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.core.cache import cache
from django.http import HttpResponse, FileResponse, Http404
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib import messages

# Python estándar
import os
import io
import logging
from collections import defaultdict
from datetime import timedelta

# Librerías de terceros para manejo de documentos DOCX
from docx import Document
from docxcompose.composer import Composer

try:
    from docxcompose.composer import ImportFormatMode
except ImportError:
    ImportFormatMode = None

from docx.shared import Pt, Inches  # Tamaño de fuente y márgenes
from docx.oxml import OxmlElement, ns
from docx.oxml.ns import qn

# Importación de vistas de autenticación propias
from .auth_views import exclude_supervisor


# Gestión de Preguntas
@exclude_supervisor
@login_required
def pregunta_list(request):
    # Perfil del usuario
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Base queryset según permisos
    if request.user.is_superuser:
        qs = Pregunta.objects.filter(usuario=user_profile)
    else:
        limite = timezone.now() - timedelta(days=1)
        qs = Pregunta.objects.filter(usuario=user_profile, fecha_creacion__gte=limite)

    # Leer filtros del GET
    universidad_id = request.GET.get('universidad')
    curso_id       = request.GET.get('curso')
    tema_id        = request.GET.get('tema')
    nivel          = request.GET.get('nivel')

    # Aplicar filtros en cascada
    if universidad_id:
        qs = qs.filter(universidad_id=universidad_id)
    if curso_id:
        qs = qs.filter(curso_id=curso_id)
    if tema_id:
        qs = qs.filter(tema_id=tema_id)
    if nivel:
        qs = qs.filter(nivel=nivel)

    # Formulario para el nivel (opcional)
    form = FiltroPreguntaForm(request.GET or None)

    # Contexto para la plantilla
    context = {
        'total_preguntas': Pregunta.objects.filter(usuario=user_profile).count(),
        'preguntas':       qs,
        'form':            form,
        'universidades':   Universidad.objects.all(),
        'cursos_para_uni': Curso.objects.filter(universidades__id=universidad_id) if universidad_id else [],
        'temas_para_curso': Tema.objects.filter(curso_id=curso_id)            if curso_id else [],
        'universidad_filter': universidad_id,
        'curso_filter':       curso_id,
        'tema_filter':        tema_id,
        'nivel_filter':       nivel,
    }
    return render(request, 'Preguntas/pregunta_list.html', context)

@login_required
def pregunta_list_supervisor(request):
    qs = Pregunta.objects.select_related('usuario__user', 'universidad', 'curso', 'tema').all()

    buscar_nombre = request.GET.get('nombre')
    if buscar_nombre:
        qs = qs.filter(nombre__icontains=buscar_nombre)

    buscar_usuario = request.GET.get('usuario')
    if buscar_usuario:
        qs = qs.filter(usuario_id=buscar_usuario)

    qs = qs.order_by('-fecha_creacion')

    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    qs_paginated = paginator.get_page(page)

    from django.contrib.auth.models import User
    usuarios = User.objects.all()

    context = {
        'preguntas': qs_paginated,
        'buscar_nombre': buscar_nombre,
        'usuarios': usuarios,
        'buscar_usuario': buscar_usuario,
    }

    return render(request, 'Preguntas/lista_supervisor.html', context)



@login_required
def pregunta_create(request):
    if request.method == 'POST':
        form = PreguntaForm(request.POST, request.FILES)
        if form.is_valid():
            pregunta = form.save(commit=False)

            # Asignar el usuario actual a la pregunta
            user_profile = UserProfile.objects.get(user=request.user)
            pregunta.usuario = user_profile

            # Asignar nombre solo si se solicita, si no se genera automáticamente
            pregunta.nombre = form.cleaned_data['nombre']
    
            count = Pregunta.objects.filter(
                universidad=pregunta.universidad,
                curso=pregunta.curso,
                tema=pregunta.tema,
                nivel=pregunta.nivel
            ).count() + 1
            pregunta.nombre = f"{pregunta.universidad.id}{pregunta.curso.id}{pregunta.tema.id}{pregunta.nivel}{count}"

            # Verificar si los campos obligatorios (universidad, curso, tema) no están vacíos
            if not pregunta.universidad or not pregunta.curso or not pregunta.tema:
                form.add_error(None, "Los campos universidad, curso y tema son obligatorios.")
                return render(request, 'Preguntas/pregunta_form.html', {'form': form, 'title': 'Nueva Pregunta'})
            
            # Guardar la pregunta
            pregunta.save()
            
            # Si se proporciona un archivo en 'contenido', asegurarse de guardarlo
            if 'contenido' in request.FILES:
                pregunta.contenido = request.FILES['contenido']
                pregunta.save()

            messages.success(request, 'Pregunta creada exitosamente.')
            return redirect('pregunta-list')

    else:
        form = PreguntaForm()

    return render(request, 'Preguntas/pregunta_form.html', {
        'form': form,
        'title': 'Nueva Pregunta'
    })


@exclude_supervisor
@login_required
def pregunta_update(request, pk):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, 'No se encontró el perfil de usuario.')
        return redirect('pregunta-list')

    if request.user.is_superuser:
        pregunta = get_object_or_404(Pregunta, pk=pk)
    else:
        pregunta = get_object_or_404(Pregunta, pk=pk, usuario=user_profile)

    if request.method == 'POST':
        form = PreguntaForm(request.POST, request.FILES, instance=pregunta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pregunta actualizada exitosamente.')
            return redirect('pregunta-list')
    else:
        form = PreguntaForm(instance=pregunta)

        # 🚫 Bloquear campos que no deben ser editables al actualizar
        campos_bloqueados = ['curso', 'universidad', 'tema']
        for campo in campos_bloqueados:
            if campo in form.fields:
                form.fields[campo].disabled = True

    return render(request, 'Preguntas/pregunta_form.html', {
        'form': form,
        'pregunta': pregunta,
        'title': 'Editar Pregunta'
    })


@exclude_supervisor
@login_required
def pregunta_delete(request, pk):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, 'No se encontró el perfil de usuario.')
        return redirect('pregunta-list')

    if request.user.is_superuser:
        pregunta = get_object_or_404(Pregunta, pk=pk)
    else:
        pregunta = get_object_or_404(Pregunta, pk=pk, usuario=user_profile)  

    if request.method == 'POST':
        pregunta.delete()
        messages.success(request, 'Pregunta eliminada exitosamente.')
        return redirect('pregunta-list')

    return render(request, 'Preguntas/pregunta_confirm_delete.html', {
        'pregunta': pregunta
    })

#desde aquí empecé a modificar lo del formato de las preguntas
#para darle 2 columnas al doc final
def set_tres_columns(section):
    sectPr = section._sectPr  # Obtener el elemento de la sección
    cols = OxmlElement('w:cols')
    cols.set(ns.qn('w:num'), '3')  # Establecer dos columnas
    sectPr.append(cols)

def set_margenes(section):
    """Configura los márgenes del documento según lo solicitado."""
    section.top_margin = Inches(2 / 2.54)  # 2 cm
    section.left_margin = Inches(0.76 / 2.54)  # 0.76 cm
    section.right_margin = Inches(0.76 / 2.54)  # 0.76 cm
    section.bottom_margin = Inches(3.25 / 2.54)  # 3.25 cm

def aplicar_formato_texto(doc):
    """Aplica Arial Narrow y tamaño 9 pt a todo el contenido del documento."""
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            run.font.name = "Arial Narrow"
            run.font.size = Pt(9)
            r = run._element
            r.rPr.rFonts.set(qn("w:eastAsia"), "Arial Narrow")
    for style in doc.styles:
        if style.type == 1:  # Solo afecta estilos de párrafo
            if style.name.lower() in ["list paragraph", "lista numerada", "lista con viñetas"]:
                style.font.name = "Arial Narrow"
                style.font.size = Pt(9)

def combinar_documentos(preguntas):
    """Combina documentos de preguntas agrupadas por curso y tema en formato de tres columnas."""
    master_doc = Document()
    master_doc.add_heading("Simulacro", level=1)
    composer = Composer(master_doc)
    
    # Configurar el documento con tres columnas y los margenes caumsa
    set_tres_columns(master_doc.sections[0])

    set_margenes(master_doc.sections[0])

    # Agrupar preguntas por curso y tema
    preguntas_ordenadas = defaultdict(lambda: defaultdict(list))

    for pregunta in preguntas:
        if pregunta.contenido and hasattr(pregunta.contenido, 'path'):
            preguntas_ordenadas[pregunta.curso.nombre][pregunta.tema.nombre].append(pregunta)

    # Iterar sobre cursos y temas
    for curso, temas in sorted(preguntas_ordenadas.items()):

        for tema, preguntas_tema in sorted(temas.items()):

            for pregunta in preguntas_tema:
                master_doc.add_heading(f"Pregunta: {pregunta.nombre}")
                sub_doc = Document(pregunta.contenido.path)

                # Aplicar formato de texto en Arial Narrow 9 pt al subdocumento
                aplicar_formato_texto(sub_doc)

                if ImportFormatMode is not None:
                    composer.append(sub_doc, import_format=ImportFormatMode.KEEP_SOURCE_FORMATTING)
                else:
                    composer.append(sub_doc)

    # Aplicar formato de texto en el documento final
    aplicar_formato_texto(master_doc)

    # Guardar el documento en memoria
    buffer = io.BytesIO()
    composer.save(buffer)
    buffer.seek(0)
    
    return buffer

logger = logging.getLogger(__name__)

def sanitize_filename(filename):
    """Sanitiza el nombre del archivo para evitar problemas"""
    # Remover caracteres problemáticos y limitar longitud
    filename = slugify(filename, allow_unicode=False)
    if len(filename) > 100:
        filename = filename[:100]
    return filename or "documento"

@xframe_options_exempt
@login_required
def vista_previa(request, pk):
    """Vista previa mejorada usando Aspose Words"""
    try:
        pregunta = Pregunta.objects.get(pk=pk)
    except Pregunta.DoesNotExist:
        logger.warning(f"Pregunta {pk} no encontrada")
        raise Http404("La pregunta no existe")

    # Validar que el archivo DOCX existe
    docx_path = os.path.join(settings.MEDIA_ROOT, str(pregunta.contenido))
    if not os.path.exists(docx_path):
        logger.error(f"Archivo DOCX no encontrado: {docx_path}")
        raise Http404("El archivo DOCX no existe")

    # Crear directorio para PDFs
    pdf_dir = os.path.join(settings.MEDIA_ROOT, 'pdfs')
    os.makedirs(pdf_dir, exist_ok=True)

    # Generar nombre seguro y único para el PDF
    safe_filename = sanitize_filename(pregunta.nombre)
    pdf_filename = f"{safe_filename}_{pregunta.id}.pdf"
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    # Verificar cache para evitar reconversiones frecuentes
    try:
        docx_mtime = os.path.getmtime(docx_path)
        cache_key = f"pdf_conversion_{pregunta.id}_{int(docx_mtime)}"
        cached_pdf_path = cache.get(cache_key)
        
        if cached_pdf_path and os.path.exists(cached_pdf_path):
            logger.info(f"Usando PDF desde cache: {cached_pdf_path}")
            return serve_pdf_file(cached_pdf_path, pregunta.nombre)
    except Exception as e:
        logger.warning(f"Error verificando cache: {e}")

    # Verificar si necesita conversión
    needs_conversion = (
        not os.path.exists(pdf_path) or 
        os.path.getmtime(docx_path) > os.path.getmtime(pdf_path)
    )

    if needs_conversion:
        logger.info(f"Iniciando conversión: {docx_path} -> {pdf_path}")
        
        try:
            # Importar y usar Aspose Words
            import aspose.words as aw
            
            # Cargar documento
            doc = aw.Document(docx_path)
            
            # Configurar opciones de guardado para PDF
            save_options = aw.saving.PdfSaveOptions()
            save_options.compliance = aw.saving.PdfCompliance.PDF17
            save_options.preserve_form_fields = True
            save_options.jpeg_quality = 90  # Calidad de imágenes
            
            # Guardar como PDF
            doc.save(pdf_path, save_options)
            
            logger.info(f"Conversión exitosa con Aspose Words")
            
            # Guardar en cache por 1 hora
            cache.set(cache_key, pdf_path, timeout=3600)
            
        except ImportError:
            logger.error("Aspose Words no está instalado")
            raise Http404("Error: Aspose Words no está disponible en el sistema")
        except Exception as e:
            logger.error(f"Error en conversión con Aspose: {e}")
            # Limpiar archivo parcial si existe
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except:
                    pass
            raise Http404(f"Error al convertir el archivo DOCX a PDF: {str(e)}")

    # Verificar que el PDF se generó correctamente
    if not os.path.exists(pdf_path):
        logger.error(f"PDF no se generó: {pdf_path}")
        raise Http404("No se pudo generar el archivo PDF")

    # Verificar que el archivo no está vacío
    try:
        file_size = os.path.getsize(pdf_path)
        if file_size == 0:
            logger.error(f"PDF generado está vacío: {pdf_path}")
            os.remove(pdf_path)
            raise Http404("El archivo PDF generado está vacío")
        elif file_size < 100:  # PDFs muy pequeños probablemente están corruptos
            logger.warning(f"PDF sospechosamente pequeño ({file_size} bytes): {pdf_path}")
    except OSError as e:
        logger.error(f"Error verificando tamaño del PDF: {e}")
        raise Http404("Error al verificar el archivo PDF generado")

    logger.info(f"Sirviendo PDF: {pdf_path} ({file_size} bytes)")
    return serve_pdf_file(pdf_path, pregunta.nombre)

def serve_pdf_file(pdf_path, original_name):
    """Función auxiliar para servir archivos PDF de forma segura"""
    try:
        pdf_file = open(pdf_path, 'rb')
        
        # Sanitizar nombre para descarga
        safe_download_name = sanitize_filename(original_name)
        download_filename = f"{safe_download_name}.pdf"
        
        # Crear respuesta
        response = FileResponse(
            pdf_file, 
            content_type='application/pdf',
            filename=download_filename
        )
        
        # Headers para mejor control de cache y seguridad
        response['Cache-Control'] = 'private, max-age=3600'  # Cache por 1 hora
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        return response
        
    except Exception as e:
        logger.error(f"Error al servir PDF {pdf_path}: {e}")
        raise Http404("Error al acceder al archivo PDF")

def cleanup_old_pdfs():
    """Limpia PDFs antiguos para ahorrar espacio"""
    try:
        pdf_dir = os.path.join(settings.MEDIA_ROOT, 'pdfs')
        if not os.path.exists(pdf_dir):
            return
        
        import time
        current_time = time.time()
        week_ago = current_time - (7 * 24 * 60 * 60)  # 7 días
        
        for filename in os.listdir(pdf_dir):
            file_path = os.path.join(pdf_dir, filename)
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                if file_mtime < week_ago:
                    try:
                        os.remove(file_path)
                        logger.info(f"PDF antiguo eliminado: {filename}")
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar {filename}: {e}")
                        
    except Exception as e:
        logger.error(f"Error en limpieza de PDFs: {e}")

@staff_member_required
def todas_las_preguntas(request):
    qs = Pregunta.objects.all()

    # Leer filtros del GET
    buscar_nombre = request.GET.get('nombre')
    usuario_id    = request.GET.get('usuario')

    # Aplicar filtros si existen
    if buscar_nombre:
        qs = qs.filter(nombre__icontains=buscar_nombre)
    if usuario_id:
        qs = qs.filter(usuario_id=usuario_id)

    # Ordenar por fecha reciente
    qs = qs.order_by('-fecha_creacion')

    # Paginación
    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    qs_paginated = paginator.get_page(page)

    context = {
        'total_preguntas': qs.count(),
        'preguntas': qs_paginated,
        'usuarios': User.objects.all(),
        'buscar_nombre': buscar_nombre,
        'usuario_id': usuario_id,
        'modo_admin': True,
    }

    return render(request, 'Preguntas/todas_las_preguntas.html', context)



@login_required
@exclude_supervisor
def descargar_preguntas(request):
    pregunta_ids = request.POST.getlist('preguntas')
    
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, "No se encontró el perfil de usuario.")
        return redirect('pregunta-list')

    preguntas = Pregunta.objects.filter(id__in=pregunta_ids, usuario=user_profile)
    
    if not preguntas:
        messages.error(request, 'No se encontraron preguntas para descargar.')
        return redirect('pregunta-list')
    
    buffer = combinar_documentos(preguntas)
    
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = 'attachment; filename="preguntas_combinadas.docx"'
    
    return response
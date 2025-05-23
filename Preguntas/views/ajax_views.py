from ..models import Universidad, Curso, Tema, Pregunta, UserProfile
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required

# AJAX
@login_required
def load_cursos(request):
    universidad_id = request.GET.get('universidad_id')
    cursos = Curso.objects.filter(universidades__id=universidad_id).distinct()
    data = [{'id': curso.id, 'nombre': curso.nombre} for curso in cursos]
    return JsonResponse(data, safe=False)

@login_required
def load_temas(request):
    curso_id = request.GET.get('curso_id')
    temas = Tema.objects.filter(curso__id=curso_id)
    data = [{'id': tema.id, 'nombre': tema.nombre} for tema in temas]
    return JsonResponse(data, safe=False)
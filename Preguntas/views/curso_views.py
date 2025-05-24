from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from ..models import Curso, Universidad
from ..forms import CursoForm
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import AdminRequiredMixin, SuccessMessageMixin, ExcludeSupervisorMixin

# UniversidadListView, UniversidadCreateView, UniversidadUpdateView, UniversidadDeleteView
# CRUD Cursos
class CursoListView(LoginRequiredMixin, ListView):
    model = Curso
    template_name = 'Preguntas/curso_list.html'
    context_object_name = 'cursos'

    def get_queryset(self):
        queryset = super().get_queryset()
        universidad_id = self.request.GET.get('universidad')
        if universidad_id:
            queryset = queryset.filter(universidades__id=universidad_id)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'universidades': Universidad.objects.all(),
            'universidad_id': self.request.GET.get('universidad')
        })
        return context

class CursoCreateView(ExcludeSupervisorMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Curso
    form_class = CursoForm
    template_name = 'Preguntas/curso_form.html'
    success_url = reverse_lazy('curso-list')
    success_message = 'Curso creado exitosamente.'

    def get_initial(self):
        initial = super().get_initial()
        universidad_id = self.request.GET.get('universidad_id')
        if universidad_id:
            initial['universidad'] = Universidad.objects.get(id=universidad_id)
        return initial

class CursoUpdateView(ExcludeSupervisorMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Curso
    form_class = CursoForm
    template_name = 'Preguntas/curso_form.html'
    success_url = reverse_lazy('curso-list')
    success_message = 'Curso actualizado exitosamente.'

class CursoDeleteView(ExcludeSupervisorMixin, AdminRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Curso
    template_name = 'Preguntas/curso_confirm_delete.html'
    success_url = reverse_lazy('curso-list')
    success_message = 'Curso eliminado exitosamente.'

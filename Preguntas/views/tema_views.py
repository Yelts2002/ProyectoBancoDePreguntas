from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from ..models import Tema, Universidad, Curso
from ..forms import TemaForm
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import AdminRequiredMixin, SuccessMessageMixin, ExcludeSupervisorMixin

#CRUDS DE TEMAS
class TemaListView(LoginRequiredMixin, ListView):
    model = Tema
    template_name = 'Preguntas/tema_list.html'
    context_object_name = 'temas'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('curso')
        filtros = {}

        curso_id = self.request.GET.get('curso')
        universidad_id = self.request.GET.get('universidad')

        if curso_id:
            filtros['curso_id'] = curso_id
        if universidad_id:
            filtros['curso__universidades__id'] = universidad_id

        return queryset.filter(**filtros) if filtros else queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'universidades': Universidad.objects.all(),
            'cursos': Curso.objects.all(),
            'universidad_id': self.request.GET.get('universidad'),
            'curso_id': self.request.GET.get('curso')
        })
        return context

class TemaCreateView(ExcludeSupervisorMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Tema
    form_class = TemaForm
    template_name = 'Preguntas/tema_form.html'
    success_url = reverse_lazy('tema-list')
    success_message = 'Tema creado exitosamente.'

    def get_initial(self):
        initial = super().get_initial()
        curso_id = self.request.GET.get('curso_id')
        if curso_id:
            initial['curso'] = Curso.objects.get(id=curso_id)
        return initial

class TemaUpdateView(ExcludeSupervisorMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Tema
    form_class = TemaForm
    template_name = 'Preguntas/tema_form.html'
    success_url = reverse_lazy('tema-list')
    success_message = 'Tema actualizado exitosamente.'

class TemaDeleteView(ExcludeSupervisorMixin, AdminRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Tema
    template_name = 'Preguntas/tema_confirm_delete.html'
    success_url = reverse_lazy('tema-list')
    success_message = 'Tema eliminado exitosamente.'
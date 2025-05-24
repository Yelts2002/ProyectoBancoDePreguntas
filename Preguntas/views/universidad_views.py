from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from ..models import Universidad
from ..forms import UniversidadForm
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import AdminRequiredMixin, SuccessMessageMixin, ExcludeSupervisorMixin

class UniversidadListView(LoginRequiredMixin, ListView):
    model = Universidad
    template_name = 'Preguntas/universidad_list.html'
    context_object_name = 'universidades'


class UniversidadCreateView(
    ExcludeSupervisorMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView
):
    model = Universidad
    form_class = UniversidadForm
    template_name = 'Preguntas/universidad_form.html'
    success_url = reverse_lazy('universidad-list')
    success_message = 'Universidad creada exitosamente.'


class UniversidadUpdateView(
    ExcludeSupervisorMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = Universidad
    form_class = UniversidadForm
    template_name = 'Preguntas/universidad_form.html'
    success_url = reverse_lazy('universidad-list')
    success_message = 'Universidad actualizada exitosamente.'


class UniversidadDeleteView(
    ExcludeSupervisorMixin, AdminRequiredMixin, SuccessMessageMixin, DeleteView
):
    model = Universidad
    template_name = 'Preguntas/universidad_confirm_delete.html'
    success_url = reverse_lazy('universidad-list')
    success_message = 'Universidad eliminada exitosamente.'

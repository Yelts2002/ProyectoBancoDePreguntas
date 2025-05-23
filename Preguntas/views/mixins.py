from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):    
    def test_func(self):
        return self.request.user.is_staff  # Solo administradores pueden acceder
    
    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para realizar esta acción.")
        raise PermissionDenied

# Mixin para mensajes de éxito en vistas basadas en clases
class SuccessMessageMixin:
    success_message = ""
    
    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)
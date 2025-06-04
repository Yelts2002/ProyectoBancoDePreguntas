from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import UserProfile
from django.contrib import admin
from django.contrib.auth.decorators import user_passes_test
from ..forms import CustomUserCreationForm
from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User

@user_passes_test(lambda u: u.is_superuser)
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            password = form.cleaned_data.get('password1')
            messages.success(
                request,
                f"✅ Usuario '{user.username}' creado exitosamente. Contraseña: {password}"
            )
            return redirect('register') 
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, username):
    if request.method == 'POST':
        user = get_object_or_404(User, username=username)
        if user != request.user:  # Evitar que se elimine a sí mismo
            user.delete()
            messages.success(request, f"Usuario '{username}' eliminado correctamente.")
        else:
            messages.error(request, "No puedes eliminar tu propio usuario.")
    return redirect('admin-dashboard')

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            try:
                user_profile = user.userprofile
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(user=user)

            if user_profile.is_active:
                login(request, user)
                next_url = request.GET.get('next', 'pregunta-list')
                return redirect(next_url)
            else:
                messages.error(request, 'Tu cuenta está suspendida. Comunícate con el administrador.')
                logout(request)
                return redirect('login')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    
    return render(request, 'registration/login.html')

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active')
    list_filter = ('is_active',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

admin.site.register(UserProfile, UserProfileAdmin)

def exclude_supervisor(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'supervisor':
            return HttpResponseForbidden("No tienes permiso para acceder aquí")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def user_logout(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('login')

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from ..models import UserProfile
from django.contrib import admin
from django.contrib.auth.decorators import user_passes_test
from ..forms import CustomUserCreationForm
from functools import wraps
from django.http import HttpResponseForbidden

# Autenticación
@user_passes_test(lambda u: u.is_superuser)
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registro exitoso. ¡Bienvenido!')
            return redirect('pregunta-list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

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

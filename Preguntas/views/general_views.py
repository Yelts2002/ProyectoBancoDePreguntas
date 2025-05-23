from django.shortcuts import render
from django.contrib.auth.decorators import login_required



# Página principal
@login_required
def home(request):
    return render(request, 'Preguntas/home.html')

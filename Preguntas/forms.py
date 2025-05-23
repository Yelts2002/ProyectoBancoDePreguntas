from django import forms
from .models import Universidad, Curso, Tema, Pregunta, User
from django.contrib.auth.forms import UserCreationForm

class UniversidadForm(forms.ModelForm):
    class Meta:
        model = Universidad
        fields = ['nombre', 'cursos']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la universidad',
            }),
            'cursos': forms.SelectMultiple(attrs={
                'class': 'form-control',
            }),
        }

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre del curso',
            }),
        }

class TemaForm(forms.ModelForm):
    class Meta:
        model = Tema
        fields = ['nombre', 'curso']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del tema',
            }),
            'curso': forms.Select(attrs={
                'class': 'form-control',
            }),
        }

class PreguntaForm(forms.ModelForm):
    add_nombre = forms.BooleanField(required=False, label="¿Deseas añadir un nombre?")

    class Meta:
        model = Pregunta
        fields = ['universidad', 'curso', 'tema', 'nivel', 'respuesta', 'nombre', 'contenido']
        widgets = {
            'universidad': forms.Select(attrs={'class': 'form-control'}),
            'curso': forms.Select(attrs={'class': 'form-control'}),
            'tema': forms.Select(attrs={'class': 'form-control'}),
            'nivel': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'respuesta': forms.Select(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'contenido': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].required = False
        self.fields['curso'].queryset = Curso.objects.none()
        self.fields['tema'].queryset = Tema.objects.none()

        if 'universidad' in self.data:
            self._filtrar_cursos_por_universidad()
        elif self.instance.pk and self.instance.universidad:
            self.fields['curso'].queryset = Curso.objects.filter(
                universidades__id=self.instance.universidad.id
            ).order_by('nombre')

        if 'curso' in self.data:
            self._filtrar_temas_por_curso()
        elif self.instance.pk and self.instance.curso:
            self.fields['tema'].queryset = Tema.objects.filter(
                curso__id=self.instance.curso.id
            ).order_by('nombre')

    def _filtrar_cursos_por_universidad(self):
        try:
            universidad_id = int(self.data.get('universidad'))
            self.fields['curso'].queryset = Curso.objects.filter(
                universidades__id=universidad_id
            ).order_by('nombre')
        except (ValueError, TypeError):
            self.fields['curso'].queryset = Curso.objects.none()

    def _filtrar_temas_por_curso(self):
        try:
            curso_id = int(self.data.get('curso'))
            self.fields['tema'].queryset = Tema.objects.filter(
                curso__id=curso_id
            ).order_by('nombre')
        except (ValueError, TypeError):
            self.fields['tema'].queryset = Tema.objects.none()

    def clean_contenido(self):
        contenido = self.cleaned_data.get('contenido')
        if contenido and contenido.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "El archivo es demasiado grande. El tamaño máximo permitido es de 5 MB."
            )
        return contenido

#filtrar 
class FiltroPreguntaForm(forms.Form):
    universidad = forms.ModelChoiceField(queryset=Universidad.objects.all(), required=False)
    curso = forms.ModelChoiceField(queryset=Curso.objects.none(), required=False)
    tema = forms.ModelChoiceField(queryset=Tema.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'universidad' in self.data:
            self._filtrar_cursos_por_universidad()

        if 'curso' in self.data:
            self._filtrar_temas_por_curso()

    def _filtrar_cursos_por_universidad(self):
        try:
            universidad_id = int(self.data.get('universidad'))
            self.fields['curso'].queryset = Curso.objects.filter(
                universidades=universidad_id
            ).order_by('nombre')
        except (ValueError, TypeError):
            pass

    def _filtrar_temas_por_curso(self):
        try:
            curso_id = int(self.data.get('curso'))
            self.fields['tema'].queryset = Tema.objects.filter(
                curso_id=curso_id
            ).order_by('nombre')
        except (ValueError, TypeError):
            pass

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'nombre@ejemplo.com'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label="Nombre",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        label="Apellido",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'}),
        }

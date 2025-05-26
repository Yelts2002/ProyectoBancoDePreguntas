from django import forms
from .models import Universidad, Curso, Tema, Pregunta, User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

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

# forms.py - Formulario corregido
class PreguntaForm(forms.ModelForm):
    class Meta:
        model = Pregunta
        fields = ['universidad', 'curso', 'tema', 'nivel', 'respuesta', 'contenido', 'nombre', 'tiene_solucion']
        widgets = {
            'universidad': forms.Select(attrs={'class': 'form-control'}),
            'curso': forms.Select(attrs={'class': 'form-control'}),
            'tema': forms.Select(attrs={'class': 'form-control'}),
            'nivel': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'respuesta': forms.Select(attrs={'class': 'form-control'}),
            'contenido': forms.FileInput(attrs={'class': 'form-control', 'accept': '.doc,.docx'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'tiene_solucion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),            
        }

    def __init__(self, *args, **kwargs):
        # Extraer el parámetro is_update
        self.is_update = kwargs.pop('is_update', False)
        super().__init__(*args, **kwargs)
        
        # Configurar campos según el modo
        if self.is_update:
            # En modo edición: hacer campos no requeridos y deshabilitados
            for campo in ['universidad', 'curso', 'tema', 'nivel', 'nombre']:
                if campo in self.fields:
                    self.fields[campo].required = False
                    self.fields[campo].disabled = True
                    self.fields[campo].widget.attrs.update({
                        'readonly': True,
                        'style': 'background-color: #f8f9fa; cursor: not-allowed;'
                    })

            # Deshabilitar campo tiene_solucion en modo edición
            if 'tiene_solucion' in self.fields:
                self.fields['tiene_solucion'].disabled = True
                self.fields['tiene_solucion'].widget.attrs.update({
                    'style': 'pointer-events: none; opacity: 0.5;'
                })
            
            # Contenido opcional en edición
            self.fields['contenido'].required = False
            
            # Configurar querysets para campos relacionados
            if self.instance.pk:
                if self.instance.universidad:
                    self.fields['curso'].queryset = Curso.objects.filter(
                        universidades__id=self.instance.universidad.id
                    ).order_by('nombre')
                
                if self.instance.curso:
                    self.fields['tema'].queryset = Tema.objects.filter(
                        curso__id=self.instance.curso.id
                    ).order_by('nombre')
        else:
            # Modo creación normal
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

    def clean(self):
        cleaned_data = super().clean()
        
        # En modo actualización, validar solo campos editables
        if self.is_update:
            # Solo validar respuesta en modo edición
            if not cleaned_data.get('respuesta'):
                raise forms.ValidationError("La respuesta es requerida.")
        
        return cleaned_data

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
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        required=True,
        label="Rol",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'role']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'}),
        }
    def save(self, commit=True):
        user = super().save(commit=commit)

        # Asigna campos adicionales antes de guardar
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()

            # Aquí es donde se asigna el rol
            user.userprofile.role = self.cleaned_data['role']
            user.userprofile.save()

        return user

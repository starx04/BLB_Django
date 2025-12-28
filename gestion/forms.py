from django import forms

class BusquedaLibroForm(forms.Form):
    termino = forms.CharField(
        label="Buscar por Título o Autor",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Harry Potter'})
    )
    isbn = forms.CharField(
        label="Buscar por ISBN",
        max_length=13,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 9780123456789'})
    )

    def clean(self):
        datos = super().clean()
        termino = datos.get("termino")
        isbn = datos.get("isbn")

        if termino:
            datos['termino'] = termino.strip()
        if isbn:
             datos['isbn'] = isbn.strip()

        if not datos.get('termino') and not datos.get('isbn'):
            raise forms.ValidationError("Ingresa un término o un ISBN.")
        
        return datos

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PerfilUsuario
from django.core.exceptions import ValidationError

class RegistroExtendidoForm(UserCreationForm):
    dni = forms.CharField(max_length=20, required=True, label="DNI / Identificación")
    direccion = forms.CharField(max_length=200, required=False, label="Dirección")
    telefono = forms.CharField(max_length=20, required=False, label="Teléfono")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)
        
    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if not dni.isdigit():
             raise ValidationError("El DNI debe contener solo números.")
        return dni

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono and not telefono.isdigit():
             raise ValidationError("El teléfono debe contener solo números.")
        return telefono

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # El perfil se crea por la señal post_save, ahora lo actualizamos
            if hasattr(user, 'perfil'):
                perfil = user.perfil
                perfil.dni = self.cleaned_data['dni']
                perfil.direccion = self.cleaned_data['direccion']
                perfil.telefono = self.cleaned_data['telefono']
                perfil.save()
        return user

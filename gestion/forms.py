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
        cleaned_data = super().clean()
        termino = cleaned_data.get("termino")
        isbn = cleaned_data.get("isbn")

        if not termino and not isbn:
            raise forms.ValidationError("Debe ingresar al menos un término de búsqueda o un ISBN.")
        
        return cleaned_data

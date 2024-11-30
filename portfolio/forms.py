from django.forms import forms


class ContactForm(forms.Form):
    subject = forms.CharField(max_length=100, label="Sujet")
    message = forms.CharField(widget=forms.Textarea, label="Message")
    name = forms.CharField(max_length=100, label="Nom")
    sender = forms.EmailField(label="Votre email")
    societe = forms.CharField(max_length=100, required=False, label="Société")  # Champ facultatif
    telephone = forms.CharField(max_length=20, required=False, label="Téléphone")  # Champ facultatif
    cc_myself = forms.BooleanField(required=False, label="Recevoir une copie")
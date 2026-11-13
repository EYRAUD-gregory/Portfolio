from django import forms


class ContactForm(forms.Form):
    subject = forms.CharField(max_length=100, label="Sujet")
    message = forms.CharField(widget=forms.Textarea, label="Message")
    name = forms.CharField(max_length=100, label="Nom")
    sender = forms.EmailField(label="Votre email")
    societe = forms.CharField(max_length=100, required=False, label="Société")  # Champ facultatif
    telephone = forms.CharField(max_length=20, required=False, label="Téléphone")  # Champ facultatif
    # Vérifié ici aussi : la case du navigateur se contourne en une requête
    consent = forms.BooleanField(
        label="Consentement",
        error_messages={'required': "Vous devez accepter la politique de confidentialité."},
    )

    def clean_subject(self):
        # Le sujet devient un en-tête de mail : un retour à la ligne y est refusé à l'envoi
        return " ".join(self.cleaned_data["subject"].split())

from django.contrib import admin
from django import forms
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html

# Register your models here.
from .models import Profile, Formation, Project, ProjectIdea

admin.site.register(Profile)
admin.site.register(Project)
admin.site.register(Formation)


class ProjectIdeasAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'convert_button')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'convert/<int:idea_id>/',
                self.admin_site.admin_view(self.convert_to_project),
                name='projectideas_convert',
            ),
        ]
        return custom_urls + urls

    def convert_to_project(self, request, idea_id):
        from django.shortcuts import get_object_or_404, redirect
        idea = get_object_or_404(ProjectIdeas, pk=idea_id)

        if request.method == 'POST':
            form = self.ConversionForm(request.POST)
            if form.is_valid():
                # Récupérer les dates
                starting_date = form.cleaned_data['starting_date']
                ending_date = form.cleaned_data['ending_date']

                # Convertir l'idée en projet
                idea.convert_to_project(starting_date, ending_date)

                # Supprimer l'idée
                idea.delete()

                # Message de succès et redirection
                self.message_user(request, f"L'idée '{idea.title}' a été convertie en projet.")
                return redirect('admin:portfolio_projectideas_changelist')  # Retourne à la liste des idées
        else:
            form = self.ConversionForm()

        context = {
            'title': f"Convertir '{idea.title}' en projet",
            'form': form,
            'idea': idea,
        }
        return render(request, 'admin/convert_to_project.html', context)

    def convert_button(self, obj):
        return format_html(
            '<a class="button" href="convert/{}/">Convertir en projet</a>', obj.id
        )
    convert_button.short_description = "Convertir"
    convert_button.allow_tags = True

    class ConversionForm(forms.Form):
        starting_date = forms.DateField(label="Date de début", required=True, widget=forms.TextInput(attrs={'type': 'date'}))
        ending_date = forms.DateField(label="Date de fin", required=True, widget=forms.TextInput(attrs={'type': 'date'}))


admin.site.register(ProjectIdea, ProjectIdeasAdmin)



from django.contrib import admin

# Register your models here.
from .models import Profile, Formation, Project, Category, Skill, Experience


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Le site n'affiche qu'un profil : un second rendrait l'affichage imprévisible
        return super().has_add_permission(request) and not Profile.objects.exists()


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'starting_date', 'ending_date')


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'starting_date', 'ending_date')
    filter_horizontal = ('skills',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'starting_date', 'ending_date')
    list_filter = ('status',)
    filter_horizontal = ('skills',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'description')
    list_filter = ('category',)

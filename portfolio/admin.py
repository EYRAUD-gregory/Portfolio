from django.contrib import admin

# Register your models here.
from .models import Profile, Formation, Project, Category, Skill, Experience

admin.site.register(Profile)
admin.site.register(Formation)
admin.site.register(Experience)


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

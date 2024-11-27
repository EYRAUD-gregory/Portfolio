from django.shortcuts import render

# Create your views here.
from .models import Profile, Formation, Project, ProjectIdea, Category


def portfolio_view(request):
    profile = Profile.objects.first()
    formations = Formation.objects.all().order_by('-starting_date')
    projects = Project.objects.all().order_by('-starting_date')
    project_ideas = ProjectIdea.objects.all()
    categories = Category.objects.prefetch_related('skills').all()

    return render(request, 'portfolio/portfolio.html', {'profile': profile,
                                                        'projects': projects,
                                                        'formations': formations,
                                                        'project_ideas': project_ideas,
                                                        'categories': categories})

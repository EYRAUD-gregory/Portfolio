from django.shortcuts import render

# Create your views here.
from .models import Profile, Project


def portfolio_view(request):
    profile = Profile.objects.first()
    projects = Project.objects.all()
    return render(request, 'portfolio/portfolio.html', {'profile': profile, 'projects': projects})

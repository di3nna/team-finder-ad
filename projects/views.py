from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django import forms
from .models import Project, Skill
from users.models import User
from django.core.paginator import Paginator

# Форма для создания/редактирования проекта
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'github_url', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

# Главная страница / список проектов


def project_list(request):
    projects = Project.objects.all().order_by('-created_at')
    all_skills = Skill.objects.all().order_by('name')
    active_skill = None
    
    skill_name = request.GET.get('skill')
    if skill_name:
        try:
            active_skill = Skill.objects.get(name=skill_name)
            projects = projects.filter(skills=active_skill)
        except Skill.DoesNotExist:
            pass
    
    paginator = Paginator(projects, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'projects/project_list.html', {
        'projects': page_obj,
        'all_skills': all_skills,
        'active_skill': active_skill,
        'page_obj': page_obj,
    })
# Страница одного проекта
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    return render(request, 'projects/project-details.html', {'project': project})


# Создание проекта (только для залогиненных)
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            project.participants.add(request.user)
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm()
    
    return render(request, 'projects/create-project.html', {'form': form, 'is_edit': False})


# Редактирование проекта (только для автора)
@login_required
def edit_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if project.owner != request.user:
        return redirect('project_detail', project_id=project_id)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'projects/create-project.html', {'form': form, 'is_edit': True, 'project': project})


# Завершить проект
@login_required
def complete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if project.owner == request.user and project.status == 'open':
        project.status = 'closed'
        project.save()
        return JsonResponse({'status': 'ok', 'project_status': 'closed'})
    return JsonResponse({'status': 'error'}, status=400)


# Добавить/удалить участника
@login_required
def toggle_participate(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user in project.participants.all():
        project.participants.remove(request.user)
        added = False
    else:
        project.participants.add(request.user)
        added = True
    return JsonResponse({'status': 'ok', 'added': added})


# Автодополнение навыков
def skill_autocomplete(request):
    q = request.GET.get('q', '')
    skills = Skill.objects.filter(name__istartswith=q)[:10]
    data = [{'id': s.id, 'name': s.name} for s in skills]
    return JsonResponse(data, safe=False)


# Добавить навык проекту
@login_required
def add_project_skill(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if project.owner != request.user:
        return JsonResponse({'error': 'no permission'}, status=403)
    
    skill_id = request.POST.get('skill_id')
    skill_name = request.POST.get('name')
    
    if skill_id:
        skill = get_object_or_404(Skill, id=skill_id)
        created = False
    else:
        skill, created = Skill.objects.get_or_create(name=skill_name)
    
    if skill in project.skills.all():
        added = False
    else:
        project.skills.add(skill)
        added = True
    
    return JsonResponse({'skill_id': skill.id, 'created': created, 'added': added})


# Удалить навык у проекта
@login_required
def remove_project_skill(request, project_id, skill_id):
    project = get_object_or_404(Project, id=project_id)
    if project.owner != request.user:
        return JsonResponse({'error': 'no permission'}, status=403)
    
    skill = get_object_or_404(Skill, id=skill_id)
    project.skills.remove(skill)
    return JsonResponse({'status': 'ok'})
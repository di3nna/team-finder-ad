# Стандартные библиотеки
import http

# Django импорты
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator

# Локальные импорты
from .models import Project, Skill, STATUS_OPEN, STATUS_CLOSED
from users.models import User
from .forms import ProjectForm

# Константы
SKILLS_SUGGESTIONS_LIMIT = 10
PROJECTS_PER_PAGE = 12


def paginate_queryset(request, queryset, items_per_page=PROJECTS_PER_PAGE):
    """Функция для пагинации queryset"""
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get("page")
    return paginator.get_page(page_number)


def get_object_or_404_json(model, **kwargs):
    """Аналог get_object_or_404 для JSON ответов"""
    obj = model.objects.filter(**kwargs).first()
    if obj is None:
        return None
    return obj


# Главная страница / список проектов
def project_list(request):
    projects = Project.objects.all().order_by("-created_at")
    all_skills = Skill.objects.all().order_by("name")
    active_skill = None

    skill_name = request.GET.get("skill")
    if skill_name:
        try:
            active_skill = Skill.objects.get(name=skill_name)
            projects = projects.filter(skills=active_skill)
        except Skill.DoesNotExist:
            pass

    page_obj = paginate_queryset(request, projects)

    return render(
        request,
        "projects/project_list.html",
        {
            "projects": page_obj,
            "all_skills": all_skills,
            "active_skill": active_skill,
            "page_obj": page_obj,
        },
    )


# Страница одного проекта
def project_detail(request, project_id):
    project = get_object_or_404_json(Project, id=project_id)
    if project is None:
        return render(request, "404.html", status=http.HTTPStatus.NOT_FOUND)
    return render(request, "projects/project-details.html", {"project": project})


# Создание проекта (только для залогиненных)
@login_required
def create_project(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            project.participants.add(request.user)
            return redirect("project_detail", project_id=project.id)
    else:
        form = ProjectForm()

    return render(
        request, "projects/create-project.html", {"form": form, "is_edit": False}
    )


# Редактирование проекта (только для автора)
@login_required
def edit_project(request, project_id):
    project = get_object_or_404_json(Project, id=project_id)
    if project is None:
        return render(request, "404.html", status=http.HTTPStatus.NOT_FOUND)

    if project.owner != request.user:
        return redirect("project_detail", project_id=project_id)

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect("project_detail", project_id=project.id)
    else:
        form = ProjectForm(instance=project)

    return render(
        request,
        "projects/create-project.html",
        {"form": form, "is_edit": True, "project": project},
    )


# Завершить проект
@login_required
def complete_project(request, project_id):
    project = get_object_or_404_json(Project, id=project_id)
    if project is None:
        return JsonResponse(
            {"status": "error", "message": "Project not found"},
            status=http.HTTPStatus.NOT_FOUND,
        )

    if project.owner == request.user and project.status == STATUS_OPEN:
        project.status = STATUS_CLOSED
        project.save()
        return JsonResponse({"status": "ok", "project_status": STATUS_CLOSED})

    return JsonResponse(
        {"status": "error", "message": "Forbidden"}, status=http.HTTPStatus.FORBIDDEN
    )


# Добавить/удалить участника
@login_required
def toggle_participate(request, project_id):
    project = get_object_or_404_json(Project, id=project_id)
    if project is None:
        return JsonResponse(
            {"status": "error", "message": "Project not found"},
            status=http.HTTPStatus.NOT_FOUND,
        )

    is_participant = project.participants.filter(id=request.user.id).exists()

    if is_participant:
        project.participants.remove(request.user)
        added = False
    else:
        project.participants.add(request.user)
        added = True

    return JsonResponse({"status": "ok", "added": added})


# Автодополнение навыков
def skill_autocomplete(request):
    search_query = request.GET.get("q", "")
    skills = Skill.objects.filter(name__istartswith=search_query)[
        :SKILLS_SUGGESTIONS_LIMIT
    ]
    data = [{"id": skill.id, "name": skill.name} for skill in skills]
    return JsonResponse(data, safe=False)


# Добавить навык проекту
@login_required
def add_project_skill(request, project_id):
    project = get_object_or_404_json(Project, id=project_id)
    if project is None:
        return JsonResponse(
            {"status": "error", "message": "Project not found"},
            status=http.HTTPStatus.NOT_FOUND,
        )

    if project.owner != request.user:
        return JsonResponse(
            {"status": "error", "message": "Permission denied"},
            status=http.HTTPStatus.FORBIDDEN,
        )

    skill_id = request.POST.get("skill_id")
    skill_name = request.POST.get("name")

    if skill_id:
        skill = get_object_or_404_json(Skill, id=skill_id)
        if skill is None:
            return JsonResponse(
                {"status": "error", "message": "Skill not found"},
                status=http.HTTPStatus.NOT_FOUND,
            )
        created = False
    else:
        skill, created = Skill.objects.get_or_create(name=skill_name)

    # Проверка, есть ли уже навык у проекта
    skill_exists = project.skills.filter(id=skill.id).exists()

    if skill_exists:
        added = False
    else:
        project.skills.add(skill)
        added = True

    return JsonResponse({"skill_id": skill.id, "created": created, "added": added})


# Удалить навык у проекта
@login_required
def remove_project_skill(request, project_id, skill_id):
    project = get_object_or_404_json(Project, id=project_id)
    if project is None:
        return JsonResponse(
            {"status": "error", "message": "Project not found"},
            status=http.HTTPStatus.NOT_FOUND,
        )

    if project.owner != request.user:
        return JsonResponse(
            {"status": "error", "message": "Permission denied"},
            status=http.HTTPStatus.FORBIDDEN,
        )

    skill = get_object_or_404_json(Skill, id=skill_id)
    if skill is None:
        return JsonResponse(
            {"status": "error", "message": "Skill not found"},
            status=http.HTTPStatus.NOT_FOUND,
        )

    project.skills.remove(skill)
    return JsonResponse({"status": "ok"})

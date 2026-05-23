# Стандартные библиотеки
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django import forms
from django.core.exceptions import ValidationError

# Локальные импорты
from .models import User


# Форма для редактирования профиля
class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['name', 'surname', 'about', 'phone', 'github_url', 'avatar']


# Форма для регистрации
class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['email', 'name', 'surname', 'phone']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if User.objects.filter(phone=phone).exists():
            raise ValidationError('Пользователь с таким телефоном уже существует')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Пароли не совпадают')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


def user_list(request):
    users = User.objects.all().order_by('id')
    return render(request, 'users/participants.html', {'participants': users})


def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, 'users/user-details.html', {'user': user})


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('project_list')
        messages.error(request, 'Неверный email или пароль')
    return render(request, 'users/login.html')


def logout_view(request):
    logout(request)
    return redirect('project_list')


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('project_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def edit_profile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user != request.user:
        return redirect('users:user_detail', user_id=user_id)

    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён')
            return redirect('users:user_detail', user_id=user.id)
    else:
        form = UserEditForm(instance=user)

    return render(request, 'users/edit_profile.html', {'form': form, 'user': user})


@login_required
def edit_my_profile(request):
    user = request.user

    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('users:user_detail', user_id=user.id)
    else:
        form = UserEditForm(instance=user)

    return render(request, 'users/edit_profile.html', {'form': form, 'user': user})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменён')
            return redirect('users:user_detail', user_id=request.user.id)
        messages.error(request, 'Ошибка при смене пароля')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/change_password.html', {'form': form})
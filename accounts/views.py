from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from accounts.decorators import require_perm
from .forms import UserCreateForm
from .models import User


@require_perm(lambda u: u.can_manage_users)
def user_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'accounts/user_list.html', {'users': users})


@require_perm(lambda u: u.can_manage_users)
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم إضافة المستخدم.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {'form': form})


@require_perm(lambda u: u.can_manage_users)
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)

    if user == request.user:
        messages.error(request, 'لا يمكنك حذف نفسك.')
        return redirect('accounts:user_list')

    if user.is_superuser:
        messages.error(request, 'لا يمكن حذف حساب مدير النظام.')
        return redirect('accounts:user_list')

    if request.method == 'POST':
        user.delete()
        messages.success(request, 'تم حذف المستخدم.')
    return redirect('accounts:user_list')


def logout_view(request):
    logout(request)
    return redirect('accounts:login')
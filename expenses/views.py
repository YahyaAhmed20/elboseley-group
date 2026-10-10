from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from accounts.decorators import require_perm
from payroll.models import Employee
from .forms import ExpenseForm
from .models import Expense, ExpenseCategory

@require_perm(lambda u: u.can_manage_operations)
def expense_list(request):
    q=request.GET.get('q','').strip(); employee=request.GET.get('employee','').strip(); category=request.GET.get('category','').strip()
    qs=Expense.objects.select_related('beneficiary','category','created_by')
    if q: qs=qs.filter(Q(beneficiary__name__icontains=q)|Q(category__name__icontains=q)|Q(note__icontains=q))
    if employee: qs=qs.filter(beneficiary_id=employee)
    if category: qs=qs.filter(category_id=category)
    total=qs.aggregate(total=Sum('amount'))['total'] or 0
    page=Paginator(qs,20).get_page(request.GET.get('page'))
    return render(request,'expenses/expense_list.html',{'expenses':page,'page_obj':page,'q':q,'employee':employee,'category':category,'employees':Employee.objects.filter(status=Employee.Status.ACTIVE),'categories':ExpenseCategory.objects.filter(is_active=True),'total':total})

@require_perm(lambda u: u.can_manage_operations)
def expense_create(request):
    form=ExpenseForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        obj=form.save(commit=False); obj.created_by=request.user; obj.save(); messages.success(request,'تم تسجيل المصروف.'); return redirect('expenses:expense_list')
    return render(request,'expenses/expense_form.html',{'form':form,'title':'إضافة مصروف'})

@require_perm(lambda u: u.can_manage_operations)
def expense_edit(request,pk):
    obj=get_object_or_404(Expense,pk=pk); form=ExpenseForm(request.POST or None,instance=obj)
    if request.method=='POST' and form.is_valid(): form.save(); messages.success(request,'تم تحديث المصروف.'); return redirect('expenses:expense_list')
    return render(request,'expenses/expense_form.html',{'form':form,'title':'تعديل المصروف'})

@require_perm(lambda u: u.can_manage_operations)
def expense_delete(request,pk):
    obj=get_object_or_404(Expense,pk=pk)
    if request.method=='POST': obj.delete(); messages.success(request,'تم حذف المصروف.')
    return redirect('expenses:expense_list')

@require_perm(lambda u: u.can_manage_operations)
def category_seed(request):
    if request.method=='POST':
        for name in ['مرتبات','كهربا','نت','نظافة','أخرى']:
            ExpenseCategory.objects.get_or_create(name=name)
        messages.success(request,'تم تجهيز بنود المصروفات.')
    return redirect('expenses:expense_list')

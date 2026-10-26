from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from accounts.decorators import require_perm
from payroll.models import Employee
from .forms import ExpenseForm
from .models import Expense, ExpenseCategory
from .services import create_expense, cancel_expense

@require_perm(lambda u: u.can_manage_operations)
def expense_list(request):
    q=request.GET.get('q','').strip(); employee=request.GET.get('employee','').strip(); category=request.GET.get('category','').strip()
    qs=Expense.objects.select_related('beneficiary','category','created_by')
    if q: qs=qs.filter(Q(beneficiary__name__icontains=q)|Q(category__name__icontains=q)|Q(note__icontains=q))
    if employee: qs=qs.filter(beneficiary_id=employee)
    if category: qs=qs.filter(category_id=category)
    total = qs.filter(is_cancelled=False).aggregate(
        total=Sum("amount")
    )["total"] or 0
    page=Paginator(qs,20).get_page(request.GET.get('page'))
    return render(request,'expenses/expense_list.html',{'expenses':page,'page_obj':page,'q':q,'employee':employee,'category':category,'employees':Employee.objects.filter(status=Employee.Status.ACTIVE),'categories':ExpenseCategory.objects.filter(is_active=True),'total':total})

@require_perm(lambda u: u.can_manage_operations)
def expense_create(request):
    form = ExpenseForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            create_expense(form=form, user=request.user)
        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                form.add_error(None, exc)
            else:
                raise
        else:
            messages.success(request, "تم تسجيل المصروف.")
            return redirect("expenses:expense_list")

    return render(
        request,
        "expenses/expense_form.html",
        {"form": form, "title": "إضافة مصروف"},
    )

@require_perm(lambda u: u.can_manage_operations)
def expense_edit(request, pk):
    obj = get_object_or_404(Expense, pk=pk)

    if obj.is_cancelled:
        messages.error(request, "لا يمكن تعديل مصروف ملغي.")
        return redirect("expenses:expense_list")

    form = ExpenseForm(request.POST or None, instance=obj)

    if request.method == "POST" and form.is_valid():
        messages.error(
            request,
            "تعديل المصروف المسجل محاسبيًا غير متاح حاليًا. "
            "يجب تنفيذ تصحيح محاسبي بدلًا من تعديل السجل مباشرة.",
        )
        return render(
            request,
            "expenses/expense_form.html",
            {"form": form, "title": "تعديل المصروف"},
        )

    return render(
        request,
        "expenses/expense_form.html",
        {"form": form, "title": "تعديل المصروف"},
    )


@require_perm(lambda u: u.can_manage_operations)
def expense_delete(request, pk):
    if request.method != "POST":
        return redirect("expenses:expense_list")

    try:
        cancel_expense(expense_id=pk, user=request.user)
    except Expense.DoesNotExist:
        messages.error(request, "المصروف غير موجود.")
    except Exception as exc:
        from django.core.exceptions import ValidationError

        if isinstance(exc, ValidationError):
            messages.error(request, "; ".join(exc.messages))
        else:
            raise
    else:
        messages.success(request, "تم إلغاء المصروف وعكس أثره المحاسبي.")

    return redirect("expenses:expense_list")


from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.shortcuts import redirect

from finance.models import Account
from .models import ExpenseCategory


@require_perm(lambda u: u.can_manage_operations)
def category_seed(request):
    if request.method == "POST":
        with transaction.atomic():
            account = Account.objects.select_for_update().filter(
                code="5000",
                is_active=True,
                account_type=Account.AccountType.EXPENSE,
            ).first()

            if account is None:
                messages.error(
                    request,
                    "تعذر تجهيز البنود: حساب مصروفات التشغيل 5000 غير موجود أو غير نشط.",
                )
                return redirect("expenses:expense_list")

            categories = [
                "مرتبات",
                "كهربا",
                "نت",
                "نظافة",
                "أخرى",
            ]

            for name in categories:
                category, _ = ExpenseCategory.objects.get_or_create(
                    name=name,
                    defaults={"account": account},
                )

                if category.account_id is None:
                    category.account = account
                    category.save(update_fields=["account"])

                elif (
                    category.account.account_type
                    != Account.AccountType.EXPENSE
                    or not category.account.is_active
                ):
                    raise ValidationError(
                        f"البند {category.name} مرتبط بحساب مصروفات غير صالح."
                    )

        messages.success(
            request,
            "تم تجهيز بنود المصروفات وربط البنود غير المرتبطة بحساب مصروفات نشط.",
        )

    return redirect("expenses:expense_list")

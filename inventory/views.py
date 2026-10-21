from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect

from accounts.decorators import require_perm
from catalog.models import Item
from .forms import (
    MovementForm,
    StockIssueForm,
    StockIssueLineFormSet,
    StockIssueEditLineFormSet,

)
from .models import StockMovement, StockIssue
from .services import (
    create_movement,
    update_movement,
    delete_movement,
    create_stock_issue,
    update_stock_issue,
    delete_stock_issue,
)


@login_required
def movement_list(request):
    q = request.GET.get('q', '').strip()
    kind = request.GET.get('kind', '').strip()
    item_id = request.GET.get('item', '').strip()
    date_from = request.GET.get('from', '').strip()
    date_to = request.GET.get('to', '').strip()

    moves = (
        StockMovement.objects
        .select_related(
            'item',
            'item__brand',
            'item__unit',
            'created_by',
        )
    )

    if q:
        moves = moves.filter(
            Q(item__name__icontains=q) |
            Q(item__brand__name__icontains=q) |
            Q(ref__icontains=q) |
            Q(notes__icontains=q)
        )

    if kind in ('in', 'out'):
        moves = moves.filter(kind=kind)

    if item_id:
        moves = moves.filter(item_id=item_id)

    if date_from:
        moves = moves.filter(
            created_at__date__gte=date_from
        )

    if date_to:
        moves = moves.filter(
            created_at__date__lte=date_to
        )

    paginator = Paginator(moves, 10)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'inventory/movement_list.html', {
        'moves': page,
        'page_obj': page,
        'q': q,
        'kind': kind,
        'item_id': item_id,
        'date_from': date_from,
        'date_to': date_to,
        'items': Item.objects.filter(
            is_active=True
        ).only('id', 'name'),
        'has_filter': any([
            q,
            kind,
            item_id,
            date_from,
            date_to,
        ]),
    })


@require_perm(lambda u: u.can_move)
def movement_create(request, kind):
    if kind not in ('in', 'out'):
        return redirect('inventory:movement_list')

    initial = {}

    item_id = request.GET.get('item')

    if item_id:
        initial['item'] = item_id

    form = MovementForm(
        request.POST or None,
        kind=kind,
        initial=initial,
    )

    if request.method == 'POST' and form.is_valid():
        try:
            create_movement(
                item_id=form.cleaned_data['item'].id,
                kind=kind,
                qty=form.cleaned_data['qty'],
                ref=form.cleaned_data['ref'],
                notes=form.cleaned_data['notes'],
                user=request.user,
            )

            messages.success(
                request,
                'تمت الحركة بنجاح.'
            )

            return redirect('inventory:movement_list')

        except ValidationError as e:
            form.add_error(None, e.message)

    return render(request, 'inventory/movement_form.html', {
        'form': form,
        'kind': kind,
        'is_edit': False,
    })


@require_perm(lambda u: u.can_move)
def movement_edit(request, pk):
    movement = get_object_or_404(
        StockMovement.objects.select_related('item'),
        pk=pk,
    )

    initial = {
        'kind': movement.kind,
        'item': movement.item_id,
        'qty': movement.qty,
        'ref': movement.ref,
        'notes': movement.notes,
    }

    form = MovementForm(
        request.POST or None,
        kind=movement.kind,
        initial=initial,
    )

    if request.method == 'POST' and form.is_valid():
        try:
            update_movement(
                movement_id=movement.pk,
                item_id=form.cleaned_data['item'].pk,
                kind=form.cleaned_data['kind'],
                qty=form.cleaned_data['qty'],
                ref=form.cleaned_data['ref'],
                notes=form.cleaned_data['notes'],
            )

            messages.success(
                request,
                'تم تعديل الحركة بنجاح.'
            )

            return redirect('inventory:movement_list')

        except ValidationError as e:
            form.add_error(None, e.message)

    return render(request, 'inventory/movement_form.html', {
        'form': form,
        'kind': movement.kind,
        'movement': movement,
        'is_edit': True,
    })


@require_perm(lambda u: u.can_move)
def movement_delete(request, pk):
    movement = get_object_or_404(
        StockMovement.objects.select_related(
            'item',
            'created_by',
        ),
        pk=pk,
    )

    if request.method == 'POST':
        try:
            delete_movement(
                movement_id=movement.pk
            )

            messages.success(
                request,
                'تم حذف الحركة بنجاح.'
            )

        except ValidationError as e:
            messages.error(
                request,
                str(e)
            )

        return redirect(
            'inventory:movement_list'
        )

    return render(
        request,
        'inventory/movement_confirm_delete.html',
        {
            'movement': movement,
        },
    )


@require_perm(lambda u: u.can_move)
def stock_issue_list(request):
    issues = (
        StockIssue.objects
        .select_related("created_by")
        .prefetch_related("lines__item")
    )

    q = request.GET.get("q", "").strip()
    if q:
        issues = issues.filter(
            Q(invoice_number__icontains=q)
            | Q(recipient__icontains=q)
            | Q(notes__icontains=q)
        )

    paginator = Paginator(issues, 10)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "inventory/stock_issue_list.html", {
        "issues": page,
        "page_obj": page,
        "q": q,
    })


@require_perm(lambda u: u.can_move)
def stock_issue_create(request):
    form = StockIssueForm(request.POST or None)
    formset = StockIssueLineFormSet(
        request.POST or None,
        prefix="lines",
    )

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        lines = [
            {
                "item_id": line["item"].pk,
                "qty": line["qty"],
                "unit_price": line["unit_price"],
            }
            for line in formset.cleaned_data
            if line and not line.get("DELETE", False)
        ]

        try:
            issue = create_stock_issue(
                invoice_number=form.cleaned_data["invoice_number"],
                recipient=form.cleaned_data["recipient"],
                issue_type=form.cleaned_data["issue_type"],
                notes=form.cleaned_data["notes"],
                lines=lines,
                user=request.user,
            )
            messages.success(request, f"تم إنشاء فاتورة الصرف {issue.invoice_number} بنجاح.")
            return redirect("inventory:stock_issue_list")

        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errors in exc.message_dict.items():
                    form.add_error(field if field in form.fields else None, errors)
            else:
                form.add_error(None, exc.messages)

    return render(request, "inventory/stock_issue_form.html", {
        "form": form,
        "formset": formset,
    })
@require_perm(lambda u: u.can_move)
def stock_issue_edit(request, pk):
    issue = get_object_or_404(
        StockIssue.objects.prefetch_related("lines__item"),
        pk=pk,
    )

    initial_lines = [
        {
            "item": line.item_id,
            "qty": line.qty,
            "unit_price": line.unit_price,
        }
        for line in issue.lines.all()
    ]

    form = StockIssueForm(
        request.POST or None,
        instance=issue,
    )

    formset_class = StockIssueEditLineFormSet

    formset = formset_class(
        request.POST or None,
        prefix="lines",
        initial=initial_lines if request.method != "POST" else None,
    )
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        lines = [
            {
                "item_id": line["item"].pk,
                "qty": line["qty"],
                "unit_price": line["unit_price"],
            }
            for line in formset.cleaned_data
            if line and not line.get("DELETE", False)
        ]

        try:
            updated_issue = update_stock_issue(
                issue_id=issue.pk,
                invoice_number=form.cleaned_data["invoice_number"],
                recipient=form.cleaned_data["recipient"],
                issue_type=form.cleaned_data["issue_type"],
                notes=form.cleaned_data["notes"],
                lines=lines,
            )

            messages.success(
                request,
                f"تم تعديل فاتورة الصرف {updated_issue.invoice_number} بنجاح.",
            )
            return redirect("inventory:stock_issue_list")

        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errors in exc.message_dict.items():
                    form.add_error(
                        field if field in form.fields else None,
                        errors,
                    )
            else:
                form.add_error(None, exc.messages)

    return render(request, "inventory/stock_issue_form.html", {
        "form": form,
        "formset": formset,
        "issue": issue,
        "is_edit": True,
    })


@require_perm(lambda u: u.can_move)
def stock_issue_delete(request, pk):
    issue = get_object_or_404(StockIssue, pk=pk)

    if request.method == "POST":
        try:
            invoice_number = issue.invoice_number
            delete_stock_issue(issue_id=issue.pk)

            messages.success(
                request,
                f"تم حذف فاتورة الصرف {invoice_number} واستعادة الكميات للمخزون.",
            )

        except ValidationError as exc:
            messages.error(request, str(exc))

        return redirect("inventory:stock_issue_list")

    return render(
        request,
        "inventory/stock_issue_confirm_delete.html",
        {"issue": issue},
    )


@require_perm(lambda u: u.can_move)
def stock_issue_detail(request, pk):
    issue = get_object_or_404(
        StockIssue.objects.select_related("created_by").prefetch_related(
            "lines__item",
            "lines__item__unit",
        ),
        pk=pk,
    )

    for line in issue.lines.all():
        line.line_total = line.qty * line.unit_price

    return render(
        request,
        "inventory/stock_issue_detail.html",
        {"issue": issue},
    )
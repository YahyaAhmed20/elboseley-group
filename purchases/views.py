from django.shortcuts import render

from django.forms import formset_factory
from django.core.exceptions import ValidationError

from .forms import PurchaseInvoiceForm, PurchaseInvoiceLineForm
from .services import create_purchase_invoice

# Create your views here.

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from accounts.decorators import require_perm
from .models import PurchaseInvoice


PurchaseInvoiceLineFormSet = formset_factory(
    PurchaseInvoiceLineForm,
    extra=0,
    min_num=1,
    max_num=10,
    validate_min=True,
    validate_max=True,
    can_delete=True,
)


@login_required
@require_perm(lambda user: user.can_manage_purchases)
def invoice_list(request):
    invoices = (
        PurchaseInvoice.objects
        .select_related("supplier", "created_by")
        .order_by("-created_at")
    )

    paginator = Paginator(invoices, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "purchases/invoice_list.html",
        {"page_obj": page_obj},
    )


@login_required
@require_perm(lambda user: user.can_manage_purchases)
def invoice_create(request):
    if request.method == "POST":
        form = PurchaseInvoiceForm(request.POST)
        formset = PurchaseInvoiceLineFormSet(
            request.POST,
            prefix="lines",
        )

        if form.is_valid() and formset.is_valid():
            lines = [
                {
                    "item_id": line["item"].pk,
                    "qty": line["qty"],
                    "unit_price": line["unit_price"],
                }
                for line in formset.cleaned_data
                if line
                and not line.get("DELETE", False)
                and line.get("item") is not None
            ]

            try:
                invoice = create_purchase_invoice(
                    supplier_id=form.cleaned_data["supplier"].pk,
                    invoice_number=form.cleaned_data["invoice_number"],
                    payment_type=form.cleaned_data["payment_type"],
                    lines=lines,
                    paid_amount=form.cleaned_data["paid_amount"],
                    notes=form.cleaned_data["notes"],
                    user=request.user,
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    f"تم إنشاء فاتورة المشتريات رقم {invoice.invoice_number} بنجاح.",
                )
                return redirect("purchases:invoice_list")
    else:
        form = PurchaseInvoiceForm()
        formset = PurchaseInvoiceLineFormSet(prefix="lines")

    return render(
        request,
        "purchases/invoice_form.html",
        {
            "form": form,
            "formset": formset,
        },
    )
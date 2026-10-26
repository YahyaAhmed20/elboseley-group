from django.shortcuts import render
from supplier.models import Supplier
from django.forms import formset_factory
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    PurchaseInvoiceForm,
    PurchaseInvoiceLineForm,
    SupplierPaymentForm,
)
from .services import create_purchase_invoice, pay_purchase_invoice

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

    suppliers = Supplier.objects.filter(is_active=True).order_by("name")
    supplier_id = request.GET.get("supplier", "").strip()

    if supplier_id.isdigit():
        invoices = invoices.filter(supplier_id=int(supplier_id))
    else:
        supplier_id = ""

    query = request.GET.get("q", "").strip()
    if query:
        invoices = invoices.filter(invoice_number__icontains=query)

    paginator = Paginator(invoices, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "purchases/invoice_list.html",
        {
            "page_obj": page_obj,
            "suppliers": suppliers,
            "selected_supplier": supplier_id,
            "q": query,
        },
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


@login_required
@require_perm(lambda user: user.can_manage_cashbox)
def invoice_pay(request, pk):
    invoice = get_object_or_404(
        PurchaseInvoice.objects.select_related("supplier"),
        pk=pk,
    )

    if request.method == "POST":
        form = SupplierPaymentForm(request.POST)

        if form.is_valid():
            try:
                pay_purchase_invoice(
                    invoice_id=invoice.pk,
                    amount=form.cleaned_data["amount"],
                    user=request.user,
                    notes=form.cleaned_data["notes"],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, "تم تسجيل سداد المورد بنجاح.")
                return redirect("purchases:invoice_list")
    else:
        form = SupplierPaymentForm()

    return render(
        request,
        "purchases/invoice_pay.html",
        {
            "invoice": invoice,
            "form": form,
        },
    )
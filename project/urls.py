from django.contrib import admin
from django.urls import path, include
from project.views import index
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('catalog/', include('catalog.urls')),
    path('inventory/', include('inventory.urls')),
    path('accounts/', include('accounts.urls')),
    path('payroll/', include('payroll.urls')),
    path('customers/', include('customers.urls')),
    path('service/', include('servicecenter.urls')),
    path('suppliers/', include('supplier.urls')),
    path('expenses/', include('expenses.urls')),
    
    path("purchases/", include("purchases.urls")),

    

   
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
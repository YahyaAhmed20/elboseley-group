from django.db import models

# Create your models here.
# inventory/models.py
from django.db import models
from django.conf import settings
from catalog.models import Item

class StockMovement(models.Model):
    class Kind(models.TextChoices):
        IN  = 'in',  'استلام'
        OUT = 'out', 'صرف'

    kind       = models.CharField(max_length=3, choices=Kind.choices)
    item       = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='movements')
    qty        = models.DecimalField(max_digits=10, decimal_places=2)
    ref        = models.CharField(max_length=50, blank=True)
    notes      = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['item', 'kind'])]
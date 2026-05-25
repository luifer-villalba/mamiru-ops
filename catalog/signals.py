from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import PriceHistory, Product
from .price_history import get_current_price_history_user

PRICE_FIELDS = ("cost_price", "sale_price", "margin_percent")


@receiver(pre_save, sender=Product)
def capture_previous_price_values(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_price_values = None
        return

    previous = sender.objects.filter(pk=instance.pk).values(*PRICE_FIELDS).first()
    instance._previous_price_values = previous


@receiver(post_save, sender=Product)
def create_price_history(sender, instance, created, **kwargs):
    previous = getattr(instance, "_previous_price_values", None)
    if created or previous is None:
        return

    changed = any(previous[field] != getattr(instance, field) for field in PRICE_FIELDS)
    if not changed:
        return

    PriceHistory.objects.create(
        product=instance,
        changed_by=get_current_price_history_user(),
        old_cost_price=previous["cost_price"],
        new_cost_price=instance.cost_price,
        old_sale_price=previous["sale_price"],
        new_sale_price=instance.sale_price,
        old_margin_percent=previous["margin_percent"],
        new_margin_percent=instance.margin_percent,
    )

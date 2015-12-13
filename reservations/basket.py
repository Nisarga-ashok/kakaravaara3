from datetime import datetime, timedelta
from shoop.front.basket.objects import BaseBasket
from shoop.front.basket.order_creator import BasketOrderCreator

from reservations.models import Reservation, ReservableProduct


class ReservableBasket(BaseBasket):
    def _compare_line_for_addition(self, current_line_data, product, supplier, shop, extra):
        if product.type.identifier == "reservable":
            # Never add to existing reservation lines
            return False
        return super(
            ReservableBasket, self)._compare_line_for_addition(current_line_data, product, supplier, shop, extra)

    def add_product(self, supplier, shop, product, quantity, force_new_line=False, extra=None, parent_line=None):
        if not extra:
            extra = {}
        if self.request.POST.get("reservation_start", None):
            extra["reservation_start"] = self.request.POST.get("reservation_start")
            extra["adults"] = self.request.POST.get("adults", 1)
            extra["children"] = self.request.POST.get("children", 0)
        # TODO: enable this here once https://github.com/shoopio/shoop/issues/291 is resolved in some way
        # Currently setting `force_new_line` causes product not to be added at all.
        # Once this works, remove above override of `_compare_line_for_addition`.
        # if product.type.identifier == "reservable":
        #     force_new_line = True
        return super(ReservableBasket, self).add_product(
            supplier, shop, product, quantity, force_new_line=force_new_line, extra=extra, parent_line=parent_line)


class ReservableOrderCreator(BasketOrderCreator):
    def process_saved_order_line(self, order, order_line):
        if order_line.product and order_line.product.type.identifier == "reservable":
            # Create reservation
            start_date = datetime.strptime(order_line.source_line.get("reservation_start"), "%Y-%m-%d")
            reservable = ReservableProduct.objects.get(product=order_line.product)
            Reservation.objects.create(
                reservable=reservable,
                order=order_line.order,
                start_time=start_date + timedelta(
                    hours=reservable.check_in_time.hour, minutes=reservable.check_in_time.minute),
                end_time=start_date + timedelta(days=int(order_line.quantity)) + timedelta(
                    hours=reservable.check_out_time.hour, minutes=reservable.check_out_time.minute),
                adults=order_line.source_line.get("adults", 1),
                children=order_line.source_line.get("children", 0)
            )
            if not order_line.extra_data:
                order_line.extra_data = {}
            order_line.extra_data["reservation_start"] = order_line.source_line.get("reservation_start")
            order_line.extra_data["adults"] = order_line.source_line.get("adults", 1)
            order_line.extra_data["children"] = order_line.source_line.get("children", 0)
            order_line.save()

from shop.inventory import getPrice, inStock
from shop.coupons import applyDiscount
from shop.tax import addTax
class Cart:
    def __init__(self):
        self.items = {}
    def add(self, item, qty=1):
        if not inStock(item, qty):
            raise ValueError("not enough stock for " + item)
        self.items[item] = self.items.get(item, 0) + qty
    def subtotal(self):
        return round(sum(getPrice(i) * q for i, q in self.items.items()), 2)
    def total(self, code=None):
        amount = self.subtotal()
        if code:
            amount = applyDiscount(amount, code)
        return addTax(amount)

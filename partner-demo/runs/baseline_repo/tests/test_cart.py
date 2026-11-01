import pytest
from shop.cart import Cart
from shop.coupons import applyDiscount
def test_subtotal():
    cart = Cart()
    cart.add("pen", 2)
    cart.add("notebook", 1)
    assert cart.subtotal() == 7.0
def test_no_code():
    cart = Cart()
    cart.add("bag", 4)
    assert cart.total() == 105.0
def test_save20():
    assert applyDiscount(100, "SAVE20") == 80.0
def test_lowercase_code():
    assert applyDiscount(50, "half") == 25.0
def test_unknown_code_keeps_total():
    assert applyDiscount(40, "FAKE") == 40.0
def test_total_with_code():
    cart = Cart()
    cart.add("bag", 4)
    assert cart.total("SAVE10") == 94.5
def test_stock_check():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add("bag", 10)

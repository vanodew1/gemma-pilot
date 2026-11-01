stock = {"pen": 50, "notebook": 20, "bag": 5, "bottle": 12}
prices = {"pen": 1.5, "notebook": 4.0, "bag": 25.0, "bottle": 8.0}
def getPrice(item):
    if item not in prices:
        raise KeyError("unknown item: " + item)
    return prices[item]
def inStock(item, qty):
    return stock.get(item, 0) >= qty

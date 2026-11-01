codes = {"SAVE10": 10, "SAVE20": 20, "HALF": 50}
def getPercent(code):
    return codes.get(code.upper(), None)
def applyDiscount(total, code):
    percent = getPercent(code)
    if percent is None:
        return total
    discounted = total * percent / 100
    return round(total - discounted, 2)

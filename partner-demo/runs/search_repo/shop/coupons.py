codes = {"SAVE10": 10, "SAVE20": 20, "HALF": 50}
def getPercent(code):
    return codes.get(code.upper(), 0)
def applyDiscount(total, code):
    percent = getPercent(code)
    discounted = total * percent / 100
    return round(total - discounted, 2)

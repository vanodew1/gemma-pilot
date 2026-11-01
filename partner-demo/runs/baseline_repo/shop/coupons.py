codes = {"SAVE10": 10, "SAVE20": 20, "HALF": 50}
def getPercent(code):
    return codes.get(code.upper(), 0)
def applyDiscount(total, code):
    percent = getPercent(code)
    if percent == 0:
        return total
    return round(total * (1 - percent / 100), 2)

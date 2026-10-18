
def calculate_total(price, tax):
    return price + calculate_tax(price, tax)


def calculate_tax(price, tax):
    return price * tax


def checkout(price, tax):
    total = calculate_total(price, tax)
    return total


def test_checkout():
    assert checkout(100, 0.1) == 110

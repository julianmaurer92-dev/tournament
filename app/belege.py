"""Betraege in Worten – fuer die Quittungen der Startgebuehren.

Aus admin.py herausgezogen (Nachtschicht 2026-10-24).
"""


def euros_to_words(amount):
    """Convert euro amount to German words for receipts."""
    if not amount:
        return "null"
    _ones = ["", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
             "acht", "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn",
             "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn"]
    _tens = ["", "", "zwanzig", "dreißig", "vierzig", "fünfzig",
             "sechzig", "siebzig", "achtzig", "neunzig"]

    def _u100(n):
        if n == 0: return ""
        if n < 20: return _ones[n]
        o = _ones[n % 10]
        return (o + "und" + _tens[n // 10]) if o else _tens[n // 10]

    def _u1000(n):
        if n == 0: return ""
        if n < 100: return _u100(n)
        return _ones[n // 100] + "hundert" + _u100(n % 100)

    n = int(amount)  # floor, not round
    cents = round((amount - n) * 100)
    if n == 0:
        word = "null"
    elif n < 1000:
        word = _u1000(n)
    elif n < 1_000_000:
        t = ("ein" if n // 1000 == 1 else _u1000(n // 1000)) + "tausend"
        word = t + _u1000(n % 1000)
    else:
        word = str(n)
    word = word.capitalize()
    if cents:
        word += f" {cents}/100"
    return word

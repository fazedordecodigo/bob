def tally(n: int, extra: int) -> int:
    if n > 0:
        n = n + 1
    # nonpositive n stays as given
    return n + extra

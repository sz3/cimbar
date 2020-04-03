
def skip_iterator(l, step):
    '''
    step should be prime. We use 31 in `decode_color`
    '''
    l = list(l)
    i = 0
    count = 0
    while count < len(l):
        i += step
        i %= len(l)
        yield l[i]
        count += 1

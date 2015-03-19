def lookup_url(link_id):
    pass


def save_url(url, wish=None):
    exists = None
    if wish is not None:
        exists = lookup_url(wish)
    if exists is None:
        pass
    pass

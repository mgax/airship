def ensure_folder(folder):
    if not folder.isdir():
        folder.makedirs()


def force_symlink(target, link):
    if link.exists() or link.islink():
        link.unlink()
    target.symlink(link)

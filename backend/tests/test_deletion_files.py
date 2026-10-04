import pytest
from app.core.deletion_files import delete_managed_file


def test_exact_deletion_and_missing_retry(tmp_path):
    (tmp_path/'private').mkdir()
    target = tmp_path/'private'/'file.pdf'
    target.write_bytes(b'private')
    other = tmp_path/'other.pdf'
    other.write_bytes(b'keep')
    delete_managed_file(tmp_path, 'private/file.pdf')
    delete_managed_file(tmp_path, 'private/file.pdf')
    assert not target.exists() and other.read_bytes() == b'keep'


@pytest.mark.parametrize('key', ['../outside', '/outside', 'a/../outside', 'a//b', 'a\\b', '', '.', 'a/'])
def test_malformed_keys_refused(tmp_path, key):
    with pytest.raises(ValueError):
        delete_managed_file(tmp_path, key)


def test_symlink_file_and_parent_refused(tmp_path):
    target = tmp_path/'keep'
    target.write_bytes(b'keep')
    (tmp_path/'link').symlink_to(target)
    with pytest.raises(ValueError):
        delete_managed_file(tmp_path, 'link')
    directory = tmp_path/'directory'
    directory.mkdir()
    (directory/'keep').write_bytes(b'keep')
    (tmp_path/'parent-link').symlink_to(directory)
    with pytest.raises(OSError):
        delete_managed_file(tmp_path, 'parent-link/keep')
    assert target.read_bytes() == b'keep' and (directory/'keep').read_bytes() == b'keep'
    delete_managed_file(tmp_path/'missing', 'file')
    with pytest.raises(ValueError):
        delete_managed_file(tmp_path, 'directory')

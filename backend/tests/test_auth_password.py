from app.auth import hash_password, verify_password


def test_hash_differs_from_plain_and_has_scheme():
    h = hash_password("correct-horse")
    assert h != "correct-horse"
    assert "correct-horse" not in h
    assert h.startswith("scrypt$")


def test_same_password_hashes_differently_salt():
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_correct_and_wrong_password():
    h = hash_password("correct-horse")
    assert verify_password("correct-horse", h) is True
    assert verify_password("wrong-horse", h) is False
    assert verify_password("", h) is False


def test_verify_handles_non_ascii_password():
    h = hash_password("비밀번호-1234")
    assert verify_password("비밀번호-1234", h) is True
    assert verify_password("비밀번호-1235", h) is False


def test_verify_broken_hash_returns_false_without_error():
    for broken in ["", "plain", "scrypt$1$2", "bcrypt$a$b$c$d$e", "scrypt$x$8$1$zz$zz"]:
        assert verify_password("anything", broken) is False

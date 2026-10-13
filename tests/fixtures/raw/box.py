def open(path: str) -> str:
    return path


class Box:
    def open(self) -> str:
        return "box"

    @staticmethod
    def make(n: int) -> int:
        return n * 2

    class Inner:
        def open(self) -> str:
            return "inner"

    def helped(self) -> int:
        def helper() -> int:
            return 1

        return helper()

    if True:
        def maybe(self) -> int:
            return 2

    @property
    def size(self) -> int:
        return 3


def outer() -> int:
    def inner() -> int:
        return 1

    return inner()


if True:

    class Late:
        def open(self) -> str:
            return "late"


def build() -> type:
    class Local:
        def open(self) -> str:
            return "local"

    return Local

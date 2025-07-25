from typing import Callable


class WorkerSettings:
    functions: list[Callable] = []

    @classmethod
    def get_function(cls, name: str) -> Callable:
        function_map = {func.__name__: func for func in cls.functions}
        if name not in function_map:
            raise ValueError(f"Function '{name}' not found in worker settings")
        return function_map[name]

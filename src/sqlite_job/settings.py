from typing import Callable


class WorkerSettings:
    def __init__(self, database_path: str):
        self.database_path = database_path
        if not hasattr(self, 'functions'):
            raise ValueError("WorkerSettings subclass must define 'functions' class attribute")
    
    def get_function(self, name: str) -> Callable:
        function_map = {func.__name__: func for func in self.functions}
        if name not in function_map:
            raise ValueError(f"Function '{name}' not found in worker settings")
        return function_map[name]

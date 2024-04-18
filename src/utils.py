class SingletonMeta(type):
    _instances = {}

    def __call(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call(*args, **kwargs)
        return cls._instances[cls]
import re
import types
from typing import Any, Literal, Union, get_args, get_origin


EmailStr = str


class FieldInfo:
    def __init__(self, default: Any = ..., default_factory: Any = None, **constraints: Any):
        self.default = default
        self.default_factory = default_factory
        self.constraints = constraints


def Field(default: Any = ..., default_factory: Any = None, **constraints: Any) -> FieldInfo:
    return FieldInfo(default, default_factory=default_factory, **constraints)


def model_validator(mode: str = "after"):
    def decorator(func):
        func.__model_validator_mode__ = mode
        return func

    return decorator


def _all_annotations(cls: type) -> dict[str, Any]:
    annotations: dict[str, Any] = {}
    for base in reversed(cls.__mro__):
        annotations.update(getattr(base, "__annotations__", {}))
    return annotations


def _convert_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise ValueError("invalid boolean")


def _convert_value(value: Any, annotation: Any) -> Any:
    if value is None:
        return None

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Literal:
        if value not in args:
            raise ValueError(f"invalid literal value: {value}")
        return value

    if origin in {Union, types.UnionType}:
        non_none_args = [arg for arg in args if arg is not type(None)]
        if value is None and len(non_none_args) != len(args):
            return None
        last_error = None
        for arg in non_none_args:
            try:
                return _convert_value(value, arg)
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error

    if annotation is bool:
        return _convert_bool(value)
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if annotation is str:
        return str(value)

    return value


def _validate_constraints(name: str, value: Any, field_info: FieldInfo | None) -> None:
    if field_info is None or value is None:
        return

    constraints = field_info.constraints
    if "min_length" in constraints and len(value) < constraints["min_length"]:
        raise ValueError(f"{name} is too short")
    if "max_length" in constraints and len(value) > constraints["max_length"]:
        raise ValueError(f"{name} is too long")
    if "ge" in constraints and value < constraints["ge"]:
        raise ValueError(f"{name} is below minimum")
    if "le" in constraints and value > constraints["le"]:
        raise ValueError(f"{name} is above maximum")
    if "pattern" in constraints and not re.match(constraints["pattern"], str(value)):
        raise ValueError(f"{name} does not match pattern")


class BaseModel:
    def __init__(self, **data: Any):
        annotations = _all_annotations(type(self))

        for name, annotation in annotations.items():
            default = getattr(type(self), name, ...)
            field_info = default if isinstance(default, FieldInfo) else None

            if name in data:
                value = data[name]
            elif field_info and field_info.default_factory is not None:
                value = field_info.default_factory()
            elif field_info and field_info.default is not ...:
                value = field_info.default
            elif default is not ... and not isinstance(default, FieldInfo):
                value = default
            else:
                raise ValueError(f"{name} is required")

            value = _convert_value(value, annotation)
            _validate_constraints(name, value, field_info)
            setattr(self, name, value)

        for attr_name in dir(type(self)):
            attr = getattr(type(self), attr_name)
            if getattr(attr, "__model_validator_mode__", None) == "after":
                result = attr(self)
                if result is not None:
                    self = result

    def model_dump(self, exclude_none: bool = False) -> dict[str, Any]:
        data = {}
        for name in _all_annotations(type(self)):
            value = getattr(self, name)
            if exclude_none and value is None:
                continue
            data[name] = value
        return data

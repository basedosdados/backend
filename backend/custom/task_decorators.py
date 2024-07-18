# -*- coding: utf-8 -*-
from datetime import datetime
from functools import wraps

from backend.apps.core.models import TaskExecution


def log_task_execution(task_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            status = "success"
            result = None
            error = None
            start_time = datetime.now()

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                status = "failed"
                error = str(e)
            finally:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                TaskExecution.objects.create(
                    task_name=task_name,
                    status=status,
                    result=result,
                    error=error,
                    execution_time=start_time,
                    duration=duration,
                )
            return result

        return wrapper

    return decorator

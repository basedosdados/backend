# -*- coding: utf-8 -*-
import traceback
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

            task_log = TaskExecution.objects.filter(status="running", task_name=task_name).first()

            if not task_log:
                task_log = TaskExecution(
                    task_name=task_name,
                    status="running",
                    execution_time=start_time,
                )

                TaskExecution.objects.bulk_create([task_log])

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                status = "failed"
                error = f"{str(e)}\n{traceback.format_exc()}"
            finally:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                task_log.status = status
                task_log.result = result
                task_log.error = error
                task_log.duration = duration
                task_log.save()
            return result

        return wrapper

    return decorator

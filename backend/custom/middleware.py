# -*- coding: utf-8 -*-
from django.core.handlers.wsgi import WSGIRequest
from django.template.response import TemplateResponse
from django.utils.deprecation import MiddlewareMixin
from loguru import logger


class LoggerMiddleware(MiddlewareMixin):
    """Log form validation errors with user and endpoint"""

    def process_template_response(self, request: WSGIRequest, response: TemplateResponse):
        try:
            errors = []
            context = response.context_data
            if context:
                if "errors" in context:
                    errors = context["errors"]
                elif "form" in context:
                    errors = context["form"].errors
            if errors:
                endpoint = request.get_full_path()
                logger.info(f"Validation errors on {request.method} {endpoint}: {repr(errors)}")
        except Exception:
            logger.exception("Error processing template response in LoggerMiddleware:")
        finally:
            return response

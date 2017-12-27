from django.utils.deprecation import MiddlewareMixin
from rest_framework.status import is_success

import logging

logger = logging.getLogger('django.request')

class ResponseFormattingMiddleware(MiddlewareMixin):
  def process_response(self, request, response):
    try:
      print('request.method', request.method)
      print('response', response)
      if request.method == 'GET' or request.content_type == 'application/json':
        response_format = {
          'result': {},
          'success': is_success(response.status_code),
          'message': response.status_text
        }

        if hasattr(response, 'data') and getattr(response, 'data') is not None:
          response_format.update({'result': response.data})
          data = response.data

          for key in response_format.keys():
            try:
              response_format[key] = data.pop(key)
            except:
              pass

        response.data = response_format
        response.content = response.rendered_content
        response['content-length'] = len(response.content)

    except:
      pass

    return response

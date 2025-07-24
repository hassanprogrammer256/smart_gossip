# views.py
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils.decorators import method_decorator
from django.http import HttpResponse, HttpResponseForbidden
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json
import logging
import hmac
import hashlib

def index(request):
   return render(request, "chat/index.html")

def group(request, group_name):
   return render(request, "chat/group.html", {"group_name": group_name})

class CSRFExemptMixin(object):
   @method_decorator(csrf_exempt)
   def dispatch(self, *args, **kwargs):
       return super().dispatch(*args, **kwargs)

@csrf_exempt
@require_http_methods(["POST"])
def stream_webhook(request):

   # Verify Stream.io webhook signature
   signature = request.headers.get('X-Signature')
   api_key = request.headers.get('X-Api-Key')
   webhook_id = request.headers.get('X-Webhook-Id')

   if not all([signature, api_key, webhook_id]):
       return HttpResponseForbidden("Missing required headers")

   try:
       # Get the raw body
       raw_body = request.body

       # Calculate expected signature
       expected_signature = hmac.new(
           settings.STREAM_API_SECRET.encode(),
           raw_body,
           hashlib.sha256
       ).hexdigest()

       # Compare signatures using constant-time comparison
       if not hmac.compare_digest(signature, expected_signature):
           return HttpResponseForbidden("Invalid signature")

       # Process the webhook data
       data = json.loads(raw_body)
       logger.info(f"Webhook data: {data}")

       event_type = data.get('type')
       if event_type == 'message.new':
           message = data['message']
           channel_id = message['cid']
           group_name = channel_id.split(':')[1]

           channel_layer = get_channel_layer()
           async_to_sync(channel_layer.group_send)(
               f'chat_{group_name}',
               {
                   'type': 'chat_message',
                   'message': message
               }
           )
       return HttpResponse(status=200)

   except Exception as e:
       return HttpResponse(status=500)
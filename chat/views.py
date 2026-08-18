import json
import asyncio
import time
import redis.asyncio as aioredis
from asgiref.sync import sync_to_async

from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.authtoken.models import Token

from .models import Message
from .serializers import MessageSerializer

# Global async Redis connection pool
async_redis_client = aioredis.Redis(
    host=settings.REDIS_HOST,
    port=6379,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)


async def verify_bearer_token(request):
    """
    Asynchronous helper to validate Bearer token authentication 
    and return the associated user, or None if invalid/unauthorized.
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    
    token_key = auth_header.split(' ')[1]
    try:
        token = await sync_to_async(Token.objects.select_related('user').get)(key=token_key)
        if token.user.is_active:
            return token.user
    except Token.DoesNotExist:
        pass
    except Exception:
        pass
    
    return None


@method_decorator(csrf_exempt, name='dispatch')
class SendMessageView(View):
    """
    Asynchronous View handling Bearer token verification, MySQL persistence, 
    and Redis Pub/Sub broadcasting.
    """
    async def post(self, request):
        user = await verify_bearer_token(request)
        if not user:
            return JsonResponse(
                {"detail": "Invalid auth token provided."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            data = json.loads(request.body)
            
            # Securely assign authenticated user's ID to auth_id
            data['auth_id'] = user.id

            serializer = MessageSerializer(data=data)
            
            is_valid = await sync_to_async(serializer.is_valid)()
            if not is_valid:
                return JsonResponse(
                    {"detail": "Invalid message provided."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            message_instance = await sync_to_async(serializer.save)()
            
            # Safe async evaluation of serializer data
            payload = await sync_to_async(lambda: MessageSerializer(message_instance).data)()
            json_payload = json.dumps(payload)
            
            # Publish live event to Redis channel & cache global pointers asynchronously
            await async_redis_client.publish('chat-channel', json_payload)
            await async_redis_client.setex('latest_chat_id', 3600, message_instance.id)
            await async_redis_client.setex('latest_chat_message', 3600, json_payload)
            
            return JsonResponse({
                "detail": payload
            }, status=status.HTTP_201_CREATED)
            
        except json.JSONDecodeError:
            return JsonResponse(
                {"detail": "Invalid JSON payload"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return JsonResponse(
                {"detail": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class ChatStreamView(View):
    """
    Production-Ready SSE Stream View for Kubernetes Environments (No Nginx):
    - 30-second maximum connection lifetime recycling window
    - Server-side stateful delta querying with strict 0-fallback for seeded history
    - True Redis Pub/Sub live event streaming (without heartbeat pings)
    """
    async def get(self, request):
        user = await verify_bearer_token(request)
        if not user:
            return JsonResponse(
                {"detail": "Invalid auth token provided."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Retrieve the user's last seen message ID from Redis session state
        redis_cursor_key = f"user_last_seen:{user.id}"
        last_seen_id_str = await async_redis_client.get(redis_cursor_key)
        
        if last_seen_id_str is not None:
            last_sent_id = int(last_seen_id_str)
        else:
            # Fallback to 0 on first connection to guarantee seeded DB backfill
            last_sent_id = 0

        # Server-Side Delta Query: Fetch only messages strictly greater than the user's last seen ID
        missed_messages = []
        try:
            new_messages = await sync_to_async(list)(
                Message.objects.filter(id__gt=last_sent_id).order_by('id')
            )
            if new_messages:
                serializer = MessageSerializer(new_messages, many=True)
                missed_messages = serializer.data
                # Update the cursor to the latest fetched message ID
                last_sent_id = new_messages[-1].id
                await async_redis_client.set(redis_cursor_key, last_sent_id)
        except Exception:
            pass

        async def event_stream():
            start_time = time.time()
            max_duration = 30  # 30-second connection lifetime recycling window

            pubsub = async_redis_client.pubsub()
            await pubsub.subscribe('chat-channel')

            try:
                # Connection success handshake
                yield f"data: {json.dumps({'detail': 'Connected to SSE stream successfully'})}\n\n"

                # Deliver server-side delta-queried missed messages first
                for msg in missed_messages:
                    yield f"data: {json.dumps(msg)}\n\n"
                    
                while True:
                    if (time.time() - start_time) > max_duration:
                        break

                    try:
                        # Non-blocking get_message with short timeout
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True, 
                            timeout=1.0
                        )

                        if message and message.get('type') == 'message':
                            chat_data = message['data']
                            parsed_msg = json.loads(chat_data)
                            msg_id = parsed_msg.get('id')
                            
                            # Stream live message to client
                            yield f"data: {chat_data}\n\n"
                            
                            # Automatically advance user's cursor state in Redis on live delivery
                            if msg_id:
                                await async_redis_client.set(redis_cursor_key, msg_id)

                    except asyncio.TimeoutError:
                        # Timeout loops back to check max_duration cleanly
                        pass

            except asyncio.CancelledError:
                pass
            except Exception as e:
                yield f"data: {json.dumps({'detail': str(e)})}\n\n"
            finally:
                await pubsub.unsubscribe('chat-channel')
                await pubsub.close()

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive' 
        return response


@method_decorator(csrf_exempt, name='dispatch')
class FetchMessagesView(View):
    """
    Fallback historical fetch endpoint backed by MySQL and secured with Bearer token validation.
    Handles server-side delta fetching using user session tracking in Redis if after_id is omitted.
    """
    async def get(self, request):
        user = await verify_bearer_token(request)
        if not user:
            return JsonResponse(
                {"detail": "Invalid auth token provided."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        after_id_param = request.GET.get('after_id', None)

        if after_id_param is None:
            redis_cursor_key = f"user_last_seen:{user.id}"
            last_seen_id_str = await async_redis_client.get(redis_cursor_key)
            after_id = int(last_seen_id_str) if last_seen_id_str is not None else 0
        else:
            try:
                after_id = int(after_id_param)
            except ValueError:
                after_id = 0

        try:
            new_messages = await sync_to_async(list)(
                Message.objects.filter(id__gt=after_id).order_by('id')
            )
            
            if new_messages:
                # Update user cursor state
                await async_redis_client.set(f"user_last_seen:{user.id}", new_messages[-1].id)

            serializer = MessageSerializer(new_messages, many=True)

            return JsonResponse({
                "detail": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return JsonResponse(
                {"detail": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
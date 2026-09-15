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


async def safe_update_cursor(redis_client, cursor_key, new_id):
    """
    Ensures the Redis user cursor only moves forward and never regresses 
    due to concurrent request race conditions.
    """
    lua_script = """
        local current = redis.call('get', KEYS[1])
        if current == false or tonumber(ARGV[1]) > tonumber(current) then
            redis.call('set', KEYS[1], ARGV[1])
            return 1
        end
        return 0
    """
    await redis_client.eval(lua_script, 1, cursor_key, new_id)


async def safe_update_latest_chat(redis_client, chat_id, json_payload):
    """
    Ensures global cache pointers only move forward and never regress 
    due to concurrent request race conditions.
    """
    lua_script = """
        local current = redis.call('get', KEYS[1])
        if current == false or tonumber(ARGV[1]) > tonumber(current) then
            redis.call('setex', KEYS[1], 3600, ARGV[1])
            redis.call('setex', KEYS[2], 3600, ARGV[2])
            return 1
        end
        return 0
    """
    await redis_client.eval(lua_script, 2, 'latest_chat_id', 'latest_chat_message', chat_id, json_payload)


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
    and Redis broadcasting matching Laravel's exact structure.
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
            
            # 1. Real-Time Broadcasting: Publish live event to Redis channel
            await async_redis_client.publish('chat-channel', json_payload)

            # 2. Store latest global pointers atomically using Lua script to prevent race conditions
            await safe_update_latest_chat(async_redis_client, message_instance.id, json_payload)
            
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
    Production-Ready SSE Stream View matching Laravel's Polling/Gap-Backfill Architecture:
    - 30-second maximum connection lifetime recycling window
    - Server-side stateful delta tracking per user with strict 0-fallback for seeded history
    - Polling loop with incremental database backfilling for multi-message gaps
    """
    async def get(self, request):
        user = await verify_bearer_token(request)
        if not user:
            return JsonResponse(
                {"detail": "Invalid auth token provided."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        redis_cursor_key = f"chat:user_last_seen:{user.id}"
        last_seen_id_str = await async_redis_client.get(redis_cursor_key)

        if last_seen_id_str is not None:
            last_sent_id = int(last_seen_id_str)
        else:
            # Force fallback to 0 on first connection.
            # Guarantees seeded database messages are backfilled even if Redis keys reset.
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
                last_sent_id = new_messages[-1].id
                
                # Update user cursor state in Redis atomically
                await safe_update_cursor(async_redis_client, redis_cursor_key, last_sent_id)
        except Exception:
            pass

        async def event_stream():
            nonlocal last_sent_id
            start_time = time.time()
            max_duration = 30  # 30-second connection lifetime recycling window

            # Connection success handshake
            yield f"data: {json.dumps({'detail': 'Connected to SSE stream successfully'})}\n\n"

            # Deliver server-side delta-queried missed messages first
            for msg in missed_messages:
                yield f"data: {json.dumps(msg)}\n\n"

            try:
                while True:
                    if (time.time() - start_time) > max_duration:
                        break  # Gracefully close connection after 30 seconds for worker recycling

                    latest_id = await async_redis_client.get('latest_chat_id')

                    # If a new message ID exists beyond what we've processed, backfill and stream them
                    if latest_id and int(latest_id) > last_sent_id:
                        intervening_messages = await sync_to_async(list)(
                            Message.objects.filter(id__gt=last_sent_id, id__lte=int(latest_id)).order_by('id')
                        )

                        if intervening_messages:
                            for msg in intervening_messages:
                                payload = await sync_to_async(lambda: MessageSerializer(msg).data)()
                                yield f"data: {json.dumps(payload)}\n\n"

                            last_sent_id = int(latest_id)
                            
                            # Automatically advance user's cursor state in Redis atomically
                            await safe_update_cursor(async_redis_client, redis_cursor_key, last_sent_id)

                    await asyncio.sleep(0.5)  # 0.5s pause to maintain non-blocking execution efficiency

            except asyncio.CancelledError:
                pass
            except Exception as e:
                yield f"data: {json.dumps({'detail': str(e)})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive' 
        return response


@method_decorator(csrf_exempt, name='dispatch')
class FetchMessagesView(View):
    """
    Fallback historical fetch endpoint backed directly by MySQL.
    Uses server-side Redis session tracking if after_id is omitted.
    """
    async def get(self, request):
        user = await verify_bearer_token(request)
        if not user:
            return JsonResponse(
                {"detail": "Invalid auth token provided."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        after_id_param = request.GET.get('after_id', None)
        redis_cursor_key = f"chat:user_last_seen:{user.id}"

        if after_id_param is None:
            last_seen_id_str = await async_redis_client.get(redis_cursor_key)
            after_id = int(last_seen_id_str) if last_seen_id_str is not None else 0
        else:
            try:
                after_id = int(after_id_param)
            except ValueError:
                after_id = 0

        try:
            messages = await sync_to_async(list)(
                Message.objects.filter(id__gt=after_id).order_by('id')
            )

            if messages:
                max_id = messages[-1].id
                # Safely update user cursor state atomically using Lua script
                await safe_update_cursor(async_redis_client, redis_cursor_key, max_id)

            serializer = MessageSerializer(messages, many=True)

            return JsonResponse({
                "detail": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return JsonResponse(
                {"detail": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
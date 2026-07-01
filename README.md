Below is a complete Postman testing guideline for your real‑time group chat application. It covers:

User registration & login (to get token)

REST endpoints (groups, messages) – authentication optional

WebSocket connection to chat rooms with real‑time messaging

Testing multiple users simultaneously

Prerequisites Your Docker containers are running: docker-compose up

You have created the chat app and performed migrations (docker-compose exec app python manage.py migrate)

Postman is installed (Desktop version, not Web version – WebSocket support requires desktop)

Register a New User (Public Endpoint) Request
Method: POST

URL: localhost:8000/api/chat/register/

Body (raw JSON):

json { "username": "alice", "password": "alice123", "email": "alice@example.com" } Expected Response (201 Created)

json { "user": { "id": 1, "username": "alice", "email": "alice@example.com" }, "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" } Save the token for later requests.

Login (Obtain Token) Request
Method: POST

URL: localhost:8000/api/chat/login/

Body (raw JSON):

json { "username": "alice", "password": "alice123" } Expected Response (200 OK)

json { "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", "user_id": 1, "username": "alice" } 3. Create a Chat Group (Authentication Optional) If your GroupListCreate view uses AllowAny, you can send this request without a token, or with a token – both will work.

Without token (public) – no Authorization header.

With token – add header: Authorization: Token a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

Request

Method: POST

URL: localhost:8000/api/chat/groups/

Headers: (only if using token) Authorization: Token YOUR_TOKEN

Body (raw JSON):

json { "name": "general" } Expected Response (201 Created)

json { "id": 1, "name": "general", "created_at": "2025-01-15T10:30:00Z" } 4. List All Groups Request

Method: GET

URL: localhost:8000/api/chat/groups/

Expected Response (200 OK)

json [ { "id": 1, "name": "general", "created_at": "2025-01-15T10:30:00Z" } ] 5. Send a WebSocket Message (Real‑time Chat) 5.1 Open a WebSocket connection in Postman Click New → WebSocket Request (or from the sidebar choose “WebSocket”).

Enter the URL: localhost:8090/ws/chat/general/

Click Connect.

Note: The WebSocket consumer does not require authentication yet (you can implement it later). So connection will succeed.

5.2 Send a JSON message In the “Message” field of the WebSocket tab, type:

json { "message": "Hello everyone!", "username": "alice" } Click Send.

5.3 Expected response (echoed by the server) The Response pane will show:

json { "message": "Hello everyone!", "username": "alice" } This confirms the server received the message and broadcast it back to the same connection.

Test Real‑time Messaging with Two Users 6.1 Register a second user Repeat step 1 for bob / bob123. Obtain his token.
6.2 Open two Postman WebSocket connections Connection A (Alice): ws://localhost:8000/ws/chat/general/

Connection B (Bob): localhost:8090/ws/chat/general/ (a second tab)

6.3 Send message from Alice In Connection A, send:

json { "message": "Hi Bob, this is Alice!", "username": "alice" } Connection A will receive the echo.

Connection B will also receive the same message (because it’s broadcast to all clients in the group).

6.4 Send reply from Bob In Connection B, send:

json { "message": "Hello Alice, nice to meet you!", "username": "bob" } Both connections receive Bob’s message.

Retrieve Message History (REST) After sending several WebSocket messages, the messages are saved to MySQL. You can retrieve them via GET.
Request

Method: GET

URL: localhost:8000/api/chat/groups/general/messages/

Expected Response (200 OK)

json [ { "id": 1, "group": 1, "user": 1, "username": "alice", "content": "Hi Bob, this is Alice!", "timestamp": "2025-01-15T10:32:00Z" }, { "id": 2, "group": 1, "user": 2, "username": "bob", "content": "Hello Alice, nice to meet you!", "timestamp": "2025-01-15T10:33:00Z" } ] 8. Logout (Invalidate Token) Request

Method: POST

URL: localhost:8000/api/chat/logout/

Headers: Authorization: Token YOUR_TOKEN

Expected Response (200 OK)

json { "message": "Successfully logged out." } After logout, the same token will no longer work for protected endpoints (if you later change permissions to IsAuthenticated). Currently, the endpoints are public, so logout is optional.
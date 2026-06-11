import json

from flask import Blueprint, Response, stream_with_context
from flask_login import login_required

from services.tcp_handler import register_sse_client, unregister_sse_client

stream_bp = Blueprint('stream', __name__, url_prefix='/api/stream')


@stream_bp.route('/events')
@login_required
def events():
    client = register_sse_client()

    def generate():
        try:
            yield 'data: ' + json.dumps({'type': 'connected'}) + '\n\n'
            while True:
                client['event'].wait(timeout=30)
                pending = list(client['queue'])
                client['queue'].clear()
                client['event'].clear()
                for data in pending:
                    yield 'data: ' + json.dumps(data) + '\n\n'
                yield 'data: ' + json.dumps({'type': 'heartbeat'}) + '\n\n'
        finally:
            unregister_sse_client(client)

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

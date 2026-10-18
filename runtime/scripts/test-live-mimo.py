"""Opt-in live smoke test. Reads only Pi's MiMo key; never prints credentials.

Run from the repo: python3 runtime/scripts/test-live-mimo.py
Makes three small MiMo Flash requests. Does not send Slack messages.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen

RUNTIME = Path(__file__).resolve().parents[1]
auth_path = Path.home() / '.pi' / 'agent' / 'auth.json'
credential = json.loads(auth_path.read_text()).get('mimo', {})
if credential.get('type') != 'api_key' or not credential.get('key'):
    raise SystemExit('Pi has no MiMo API-key credential')

with tempfile.TemporaryDirectory(prefix='wingman-live-mimo-') as directory:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    token = secrets.token_hex(32)
    env = {**os.environ, 'PI_PROVIDER': 'mimo', 'LLM_MODEL': 'mimo-v2.6-flash',
           'XIAOMI_TOKEN_PLAN_SGP_API_KEY': credential['key'],
           'PI_RUNTIME_TOKEN': token, 'PI_DATA_DIR': directory,
           'PI_HOST': '127.0.0.1', 'PI_PORT': str(port),
           'LLM_TEMPERATURE': '0', 'LLM_MAX_TOKENS': '512'}
    base = f'http://127.0.0.1:{port}'
    child = None
    log = tempfile.TemporaryFile()

    def request(path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = Request(base + path, data=data, headers={
            'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with urlopen(req, timeout=10) as response:
            return json.load(response)

    def start():
        global child
        child = subprocess.Popen(['node', 'server.mjs'], cwd=RUNTIME, env=env,
                                 stdout=log, stderr=log)
        for _ in range(100):
            if child.poll() is not None:
                raise RuntimeError('Runtime exited before becoming healthy')
            try:
                request('/health')
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError('Runtime startup timed out')

    def stop():
        global child
        if child and child.poll() is None:
            child.kill()
            child.wait(timeout=10)

    def wait(job):
        for _ in range(1200):
            state = request('/jobs/' + job['id'])
            if state['status'] == 'done':
                return state['result']
            if state['status'] in ('failed', 'delivery_failed'):
                # Do not echo provider errors, which can include request details.
                raise RuntimeError('Live MiMo job failed; no provider details logged')
            time.sleep(0.25)
        raise RuntimeError('Live MiMo job timed out')

    marker = 'ORBIT-' + secrets.token_hex(3).upper()
    first = {'request_id': 'live-first', 'conversation_id': 'live-conversation',
             'question': 'What is the staging verification code? Reply only with the code.',
             'context': f'The staging verification code is {marker}.',
             'sources': [{'source': 'live-test-fixture'}]}
    try:
        start()
        job = request('/jobs', first)
        time.sleep(0.3)
        interrupted = request('/jobs/' + job['id'])['status'] == 'pending'
        stop()
        start()
        answer = wait(job)
        assert marker in answer['answer'], 'Answer did not use retrieved context'
        assert answer['confidence'] == 'high'
        print('PASS live MiMo grounded answer after runtime restart')
        print('Interrupted before completion:', interrupted)
        repeated = request('/jobs', first)
        assert repeated['id'] == job['id']
        assert wait(repeated) == answer
        with sqlite3.connect(Path(directory) / 'jobs.sqlite') as db:
            assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0] == 1
        print('PASS duplicate request returns the persisted answer and one job')
        backend = RUNTIME.parent / 'backend'
        python = backend / '.venv' / 'bin' / 'python'
        checked = subprocess.run([str(python), '-c',
            'import json,sys; from app.agent_runtime import generate; '
            'print(json.dumps(generate(json.load(sys.stdin))))'],
            cwd=backend, env={**env, 'PI_RUNTIME_URL': base},
            input=json.dumps(first), text=True, capture_output=True, timeout=30)
        if checked.returncode:
            raise RuntimeError('Python runtime client failed; no credential-bearing diagnostics logged')
        assert json.loads(checked.stdout) == answer
        print('PASS Python backend client receives the same persisted live answer')
        followup = {**first, 'request_id': 'live-followup', 'context': '', 'sources': [],
                    'question': 'What staging verification code did we discuss? Reply only with the code.'}
        followup_answer = wait(request('/jobs', followup))
        assert marker in followup_answer['answer'], f"Expected {marker}; follow-up returned {followup_answer['answer']!r}"
        print('PASS live follow-up remembers the conversation across restart')
        isolated = {**followup, 'request_id': 'live-isolated', 'conversation_id': 'different-conversation',
                    'question': 'What verification code did I give you? If none, reply UNKNOWN.'}
        isolated_answer = wait(request('/jobs', isolated))
        assert marker not in isolated_answer['answer'], 'Conversation history leaked'
        print('PASS separate conversation does not inherit the code')
        print('Model: mimo-v2.6-flash; endpoint: Singapore token plan; Slack messages sent: 0')
    finally:
        stop()
        log.close()

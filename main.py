import os
import logging
import json
import base64

from flask import jsonify, make_response
from google.cloud import firestore_v1


def make_problem_json(title, status):
    return make_response(jsonify({'title': title, 'status': status}), status)


def catch_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.exception(f'Exception occurred: {e}')
            return make_problem_json('Internal error', 500)
    return wrapper


def authorize(request):
    '''Checks authorization of user specified by proxy in UserInfo header'''

    oauth_required_role = os.getenv('OAUTH_REQUIRED_ROLE')
    if not oauth_required_role:
        logging.error("Firestore-api cloud function is deployed without OAUTH_REQUIRED_ROLE")
        return make_problem_json('Internal error', 500)

    esp_auth_header = request.headers.get('X-Endpoint-API-UserInfo')
    roles = []

    if not esp_auth_header:
        logging.info('No X-Endpoint-API-UserInfo header')
        return make_problem_json('Unauthenticated', 401)
    else:
        esp_auth_json = json.loads(base64.urlsafe_b64decode(esp_auth_header +
                                                            '=' * (4 - len(esp_auth_header) % 4)))
        logging.info(f'auditLog:Request Url: {request.url} | IP: {esp_auth_json.get("ipaddr")} | \
                     User-Agent: {request.headers.get("User-Agent")} | UPN: {esp_auth_json.get("upn")}')
        roles = esp_auth_json.get('roles')

    if roles and oauth_required_role in roles:
        return make_response(jsonify({'data': 'to be specified'}), 200)
    else:
        return make_problem_json('Forbidden, missing required role', 403)


@catch_error
def handler(request):
    '''Returns data from a firestore query.'''

    auth_response = authorize(request)

    if auth_response.status_code != 200:
        return auth_response

    arguments = dict(request.args)
    arguments.pop('key', None)
    path = request.view_args['path']
    collection = path.split('/')[1]

    db = firestore_v1.Client()
    q = db.collection(collection)

    max = int(os.getenv('MAX', 3000))
    page_size = int(arguments.pop('page_size', max))
    if page_size > max:
        page_size = max
    q = q.limit(page_size)

    if arguments.get('next_cursor'):
        id = arguments.pop('next_cursor')
        snapshot = db.collection(collection).document(id).get()
        logging.info(f'Starting query at cursor: {id}')
        if snapshot:
            q = q.start_after(snapshot)

    # Return filtered documents with IN query
    multi = request.args.to_dict(flat=False)
    for field, values in multi.items():
        if len(values) > 1:
            logging.info(f'Filtering {field} in {values}')
            q = q.where(field, 'in', values)
            arguments.pop(field, None)

    # Return filtered documents
    for field, value in arguments.items():
        logging.info(f'Filtering {field} == {value}')
        q = q.where(field, '==', value)

    docs = q.stream()
    results = []
    for doc in docs:
        results.append(doc.to_dict())

    next = ''
    size = len(results)
    if results and (page_size == size):
        next = f'/{collection}?next_cursor={doc.id}&page_size={page_size}'
        for field, value in arguments.items():
            next = next + f'&{field}={value}'

    logging.info(f'Returning {size} record(s)!')

    response = {
        'status': 'success',
        'page_size': size,
        'max': max,
        'next': next,
        'results': results
    }

    return make_response(jsonify(response), 200, {'cache-control': 'private, max-age=3600, s-maxage=3600'})

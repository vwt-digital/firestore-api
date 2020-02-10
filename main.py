import os
import utils
import config
import logging

from flask import jsonify, make_response
from google.cloud import firestore_v1


def catch_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.exception(f'Exception occurred: {e}')
            return jsonify({'status': 'error'}), 500
    return wrapper


@catch_error
def handler(request):
    '''Returns data from a firestore query.'''

    arguments = dict(request.args)
    secret = utils.decrypt_secret(
        config.api['project'],
        config.api['region'],
        config.api['keyring'],
        config.api['key'],
        config.api['secret_base64']
    )
    if not arguments.get('key') == secret:
        return ('Unauthorized!', 403)
    arguments.pop('key', None)
    path = request.view_args['path']
    collection = path.split('/')[1]

    db = firestore_v1.Client()
    q = db.collection(collection)

    max = int(os.getenv('MAX', 3000))
    limit = int(arguments.get('limit', max))
    arguments.pop('limit', None)
    if limit > max:
        limit = max
    q = q.limit(limit)

    start = int(arguments.get('start', 0))
    arguments.pop('start', None)
    q = q.offset(start)

    for field, value in arguments.items():
        q = q.where(field, '==', value)

    docs = q.stream()

    results = []
    for doc in docs:
        results.append(doc.to_dict())

    size = len(results)
    previous, next = pagination(start, limit, size, collection, arguments)
    logging.info(f'Returning {size} records!')

    response = {
        'status': 'success',
        'size': size,
        'max': max,
        'next': next,
        'previous': previous,
        'results': results
    }

    return make_response(jsonify(response), 200, {'cache-control': 'private, max-age=3600, s-maxage=3600'})


def pagination(start, limit, size, coll, args):
    '''Returns the previous and next page for a data request.'''

    params = ''
    for field, value in args.items():
        params = params + f'&{field}={value}'

    if size < limit:
        next = ''
    if start == 0:
        previous = ''
    if size == limit:
        begin = start + limit
        next = f'/{coll}?start={begin}&limit={limit}{params}'
    if start > 0:
        begin = max(start - limit, 0)
        previous = f'/{coll}?start={begin}&limit={limit}{params}'

    return previous, next

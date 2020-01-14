import logging

from functools import wraps
from flask import jsonify
from google.cloud import firestore_v1


def handler_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            logging.error(f'Something went wrong: {e}')
            response = {
                'status': 'error'
            }
            return jsonify(response), 500
    return wrapper


def handler(request):
    arguments = dict(request.args)
    print(request.args)
    path = request.view_args['path']
    print(path)
    collection = path.split('/')[1]
    db = firestore_v1.Client()
    q = db.collection(collection)

    max = 3000
    limit = arguments.get('limit', None)
    if limit:
        arguments.pop('limit')
        q = q.limit(int(limit))

    offset = arguments.get('offset', None)
    if offset:
        arguments.pop('offset')
        q = q.limit(int(offset))

    for field, value in arguments.items():
        q = q.where(field, '==', value)

    docs = q.stream()

    results = []
    for doc in docs:
        results.append(doc.to_dict())

    logging.info(f'Found {len(results)} records!')

    response = {
        'status': 'success',
        'count': len(results),
        'limit': limit,
        'max': max,
        'next': path,
        'previous': path,
        'results': results
    }

    return jsonify(response), 200

import os
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

    for field, value in arguments.items():
        q = q.where(field, '==', value)

    results = []
    docs = q.stream()
    for doc in docs:
        results.append(doc.to_dict())

    next = ''
    size = len(results)
    if results and (page_size == size):
        next = f'/{collection}?next_cursor={doc.id}&page_size={page_size}'
        for field, value in arguments.items():
            next = next + f'&{field}={value}'

    logging.info(f'Returning {size} records!')

    response = {
        'status': 'success',
        'page_size': size,
        'max': max,
        'next': next,
        'results': results
    }

    return make_response(jsonify(response), 200, {'cache-control': 'private, max-age=3600, s-maxage=3600'})

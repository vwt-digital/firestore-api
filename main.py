import logging

from flask import jsonify
from google.cloud import firestore_v1

db = firestore_v1.Client()


def handler(request):
    arguments = dict(request.args)
    path = request.view_args['path']
    collection = path.split('/')[1]
    q = db.collection(collection)

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

    result = []
    for doc in docs:
        result.append(doc.to_dict())

    logging.info(f'Found {len(result)} records!')

    return jsonify(result), 200

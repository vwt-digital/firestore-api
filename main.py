import utils
import config
import logging

from flask import jsonify
from google.cloud import firestore_v1

db = firestore_v1.Client()
secret = utils.decrypt_secret(
    config.api['project'],
    config.api['region'],
    config.api['keyring'],
    config.api['key'],
    config.api['secret_base64']
)


def handler(request):
    arguments = dict(request.args)
    if not arguments.get('apiKey') == secret:
        return ('Unauthorized!', 403)
    arguments.pop('apiKey')

    if not request.method == 'GET':
        return ('Method not allowed!', 405)

    path = request.view_args['path']
    collection = path.split('/')[1]

    col_refs = db.collections()
    collections = [col.id for col in col_refs]
    if collection not in collections:
        return ('Not found!', 404)

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

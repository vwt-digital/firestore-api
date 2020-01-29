# Firestore API

This repository contains a Firestore API written in Python 3.7. The API can be deployed to GCP executing the following steps.

- Create dispatch.yaml
- Create openapi.yaml
- Include cloudbuild.yaml in your own cloudbuild.yaml:

```
# Include cloudbuild sub step
- name: 'gcr.io/cloud-builders/gcloud'
  args:
  - 'builds'
  - 'submit'
  - '--config cloudbuild.yaml'
```

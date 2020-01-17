gcloud functions deploy ${PROJECT_ID}-firestore-api \
  --entry-point=handler \
  --runtime=python37 \
  --trigger-http \
  --project=${PROJECT_ID} \
  --region=europe-west1 \
  --timeout=300s \
  --memory=2048MB \
  --set-env-vars=MAX=3000

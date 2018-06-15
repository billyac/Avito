BUCKET_NAME=chenmin-622
JOB_NAME=avito_$(date +%Y%m%d_%H%M%S)
OUTPUT_PATH=gs://$BUCKET_NAME/Avito/$JOB_NAME
TRAIN_DATA=gs://$BUCKET_NAME/Avito/pickles/
gcloud ml-engine jobs submit training $JOB_NAME \
  --job-dir $OUTPUT_PATH \
  --runtime-version 1.4  \
  --module-name Avito.train \
  --package-path Avito \
  --region us-central1 \
  --scale-tier BASIC_GPU \
  -- \
  --train-files $TRAIN_DATA \
  --config xgboost_config

#!/bin/bash

# GCP Deployment Script for BarberSync Backend
# This script builds the container using Cloud Build and deploys to Cloud Run.

set -e

# --- Configuration (Override with env vars) ---
PROJECT_ID=$(gcloud config get-value project)
REGION=${REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"barbersync-backend"}
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment for $SERVICE_NAME to $REGION in project $PROJECT_ID...${NC}"

# 1. Enable APIs (Optional, but recommended for first-time runs)
if [[ "$1" == "--init" ]]; then
    echo -e "${GREEN}📦 Enabling required GCP APIs...${NC}"
    gcloud services enable run.googleapis.com \
                           cloudbuild.googleapis.com \
                           artifactregistry.googleapis.com
fi

# 2. Build and Push using Cloud Build
# This is faster than local docker build/push and doesn't require local Docker
echo -e "${GREEN}🛠 Building and pushing image using Cloud Build...${NC}"
gcloud builds submit --tag $IMAGE_NAME .

# 3. Deploy to Cloud Run
echo -e "${GREEN}🚢 Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="POSTGRES_SERVER=YOUR_CLOUD_SQL_IP,POSTGRES_DB=barbersync,POSTGRES_USER=postgres,POSTGRES_PASSWORD=YOUR_PASSWORD" \
    --port 8080

echo -e "${GREEN}✅ Deployment complete!${NC}"
gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)'

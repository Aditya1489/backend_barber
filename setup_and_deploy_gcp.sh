#!/bin/bash

# Unified GCP Setup & Deployment Script for BarberSync
# This script handles:
# 1. Project Initialization & API enablement
# 2. Cloud SQL (PostgreSQL) Creation
# 3. Backend Deployment to Cloud Run

set -e

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration (Priority: ENV > .env > Defaults)
PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project)}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME=${GCP_SERVICE_NAME:-"barbersync-backend"}
DB_INSTANCE_NAME="barbersync-db"
DB_NAME="barbersync"
DB_PASSWORD=${POSTGRES_PASSWORD:-"aditya_db_password"} # Use existing password or default
BUCKET_NAME=${GCS_BUCKET_NAME:-"barbersync-uploads-$PROJECT_ID"}
REPO_NAME="barbersync-repo"

IMAGE_NAME="${REGION}-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}    🚀 UNIFIED GCP DEPLOYMENT STARTED${NC}"
echo -e "${BLUE}==================================================${NC}"

# 1. Initialization
echo -e "\n${GREEN}[1/4] Initializing Project & APIs...${NC}"
gcloud config set project $PROJECT_ID
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
BUILD_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

echo -e "${BLUE}Ensuring Cloud Build & Compute SAs have Cloud SQL Client role...${NC}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$BUILD_SA" \
    --role="roles/cloudsql.client" >/dev/null 2>&1 || true

COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/cloudsql.client" >/dev/null 2>&1 || true

gcloud services enable run.googleapis.com \
                       cloudbuild.googleapis.com \
                       artifactregistry.googleapis.com \
                       sqladmin.googleapis.com \
                       storage.googleapis.com

# 2. Database & Storage Setup
echo -e "\n${GREEN}[2/4] Setting up Database & Storage...${NC}"
if ! gcloud sql instances describe $DB_INSTANCE_NAME >/dev/null 2>&1; then
    echo -e "${BLUE}Creating new Cloud SQL instance: $DB_INSTANCE_NAME (this may take a few minutes)...${NC}"
    gcloud sql instances create $DB_INSTANCE_NAME \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --root-password=$DB_PASSWORD
else
    echo -e "${BLUE}Cloud SQL instance $DB_INSTANCE_NAME already exists.${NC}"
fi

# Ensure Database exists
echo -e "${BLUE}Ensuring database '$DB_NAME' exists...${NC}"
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE_NAME --quiet || true

# Ensure User/Password correctly set
echo -e "${BLUE}Ensuring 'postgres' user has the correct password...${NC}"
gcloud sql users set-password postgres --instance=$DB_INSTANCE_NAME --password=$DB_PASSWORD --quiet

# Create GCS Bucket if it doesn't exist
if ! gsutil ls -b gs://$BUCKET_NAME >/dev/null 2>&1; then
    echo -e "${BLUE}Creating GCS Bucket: gs://$BUCKET_NAME...${NC}"
    gsutil mb -l $REGION gs://$BUCKET_NAME
    # Make objects publicly readable by default (common for avatar/photos)
    gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME
else
    echo -e "${BLUE}GCS Bucket $BUCKET_NAME already exists.${NC}"
fi

# Create Artifact Registry Repository if it doesn't exist
echo -e "${BLUE}Ensuring Artifact Registry Repository exists: $REPO_NAME...${NC}"
gcloud artifacts repositories create $REPO_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for BarberSync" \
    --quiet >/dev/null 2>&1 || true

# Get Instance Details
DB_IP=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(ipAddresses[0].ipAddress)")
INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)")
echo -e "${BLUE}Database IP: $DB_IP${NC}"
echo -e "${BLUE}Instance Connection: $INSTANCE_CONNECTION_NAME${NC}"

# 3. Backend Deployment
echo -e "\n${GREEN}[3/4] Building Container Image...${NC}"

# Build and Push Container via Cloud Build
echo -e "${BLUE}Building $IMAGE_NAME...${NC}"
gcloud builds submit --tag $IMAGE_NAME .

echo -e "\n${GREEN}[4/4] Deploying to Cloud Run...${NC}"
echo -e "${BLUE}Deploying $SERVICE_NAME to $REGION (with Auto-Migrations)...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --add-cloudsql-instances $INSTANCE_CONNECTION_NAME \
    --set-env-vars="POSTGRES_SERVER=$DB_IP,POSTGRES_DB=$DB_NAME,POSTGRES_USER=postgres,POSTGRES_PASSWORD=$DB_PASSWORD,JWT_SECRET=$JWT_SECRET,GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY,OTP_PROVIDER=$OTP_PROVIDER,ENVIRONMENT=production,GCS_BUCKET_NAME=$BUCKET_NAME,RUN_MIGRATIONS=true,DB_INSTANCE_NAME=$INSTANCE_CONNECTION_NAME" \
    --port 8080

echo -e "\n${BLUE}==================================================${NC}"
echo -e "${GREEN}    ✅ DEPLOYMENT COMPLETE!${NC}"
echo -e "${BLUE}==================================================${NC}"
echo -en "${GREEN}Service URL: ${NC}"
gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)'

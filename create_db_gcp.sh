#!/bin/bash

# Configuration
PROJECT_ID=$(gcloud config get-value project)
INSTANCE_NAME="barbersync-db"
DATABASE_VERSION="POSTGRES_15"
REGION="us-central1"
TIER="db-f1-micro" # Smallest tier for dev/learning
DB_NAME="barbersync"
DB_USER="postgres"
DB_PASSWORD="aditya_db_password" # CHANGE THIS

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}🚀 Creating Cloud SQL instance: $INSTANCE_NAME...${NC}"

# 1. Create Instance
gcloud sql instances create $INSTANCE_NAME \
    --database-version=$DATABASE_VERSION \
    --tier=$TIER \
    --region=$REGION \
    --root-password=$DB_PASSWORD

# 2. Create Database
echo -e "${GREEN}📂 Creating database $DB_NAME...${NC}"
gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME

# 3. Create User (Optional if using root)
# echo -e "${GREEN}👤 Creating user $DB_USER...${NC}"
# gcloud sql users create $DB_USER --instance=$INSTANCE_NAME --password=$DB_PASSWORD

echo -e "${GREEN}✅ Cloud SQL instance created successfully!${NC}"
echo -e "${GREEN}📝 Instance IP Address:${NC}"
gcloud sql instances describe $INSTANCE_NAME --format="value(ipAddresses.ipAddress)"

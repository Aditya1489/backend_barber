# GCP Deployment Guide (Cloud Run)

## 1. Fast Track (Recommended) 🚀

I've created a unified script that handles everything—API enablement, Database creation, and Backend deployment—in one go.

```bash
chmod +x setup_and_deploy_gcp.sh
./setup_and_deploy_gcp.sh
```

---

## 2. Prerequisites

- [ ] **GCP Project**: Create a project in the [GCP Console](https://console.cloud.google.com/).
- [ ] **gcloud CLI**: Install and initialize the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
  - Run `gcloud auth login` and `gcloud config set project YOUR_PROJECT_ID`.
- [ ] **Billing**: Ensure billing is enabled for your project.

## 3. Database Setup (Cloud SQL)

Cloud Run is serverless and requires a managed database like **Cloud SQL**.

### A. Automatic Provisioning
The unified script handles this, but you can also run the database-specific helper:
```bash
chmod +x create_db_gcp.sh
./create_db_gcp.sh
```

### B. Connection String
Once created, get your instance IP:
`gcloud sql instances describe barbersync-db --format="value(ipAddresses.ipAddress)"`

Update your `.env` or deployment script `set-env-vars`:
`DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@INSTANCE_IP/barbersync`

## 4. Security Best Practices

- **Secrets**: Instead of hardcoding keys in the script, use [Secret Manager](https://cloud.google.com/secret-manager).
- **Service Account**: Ensure the Cloud Run service account has `Cloud SQL Client` permissions.

---

## 5. Migrating Existing Data (Optional) 💾

If you want to move your *actual data* (users, bookings) from local to GCP:

1.  **Export Local Data**:
    ```bash
    pg_dump -h localhost -U postgres -d barbersync > backup.sql
    ```
2.  **Import to GCP**:
    Using the Cloud SQL Auth Proxy (see Section 3C):
    ```bash
    psql -h 127.0.0.1 -U postgres -d barbersync < backup.sql
    ```

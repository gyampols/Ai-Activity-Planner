#!/bin/bash
# Script to grant all required permissions to the CircleCI service account
# Run this locally with your gcloud CLI configured

PROJECT_ID="ai-activity-planner-480420"
SERVICE_ACCOUNT="circleci-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Granting permissions to: $SERVICE_ACCOUNT"
echo "Project: $PROJECT_ID"
echo ""

# Required roles for Cloud Run deployment from source
ROLES=(
  "roles/run.admin"                    # Deploy and manage Cloud Run services
  "roles/iam.serviceAccountUser"       # Act as service accounts
  "roles/storage.admin"                # Access Cloud Storage (for Cloud Build)
  "roles/artifactregistry.writer"      # Write to Artifact Registry
  "roles/cloudbuild.builds.editor"     # Create and manage Cloud Build builds
)

for ROLE in "${ROLES[@]}"; do
  echo "Granting $ROLE..."
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="$ROLE" \
    --quiet
  
  if [ $? -eq 0 ]; then
    echo "✓ Successfully granted $ROLE"
  else
    echo "✗ Failed to grant $ROLE"
  fi
  echo ""
done

echo "All permissions granted!"
echo ""
echo "Service account roles:"
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SERVICE_ACCOUNT" \
  --format="table(bindings.role)"

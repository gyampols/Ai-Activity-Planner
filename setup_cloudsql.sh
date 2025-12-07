#!/bin/bash
# Automated Cloud SQL Setup Script
# Run this once the Cloud SQL instance is ready

set -e  # Exit on error

echo "🔍 Checking Cloud SQL instance status..."
STATUS=$(gcloud sql instances describe ai-planner-db --format="value(state)")

if [ "$STATUS" != "RUNNABLE" ]; then
    echo "❌ Cloud SQL instance is not ready yet (Status: $STATUS)"
    echo "Please wait a few more minutes and run this script again."
    exit 1
fi

echo "✅ Cloud SQL instance is ready!"
echo ""

# Step 1: Create database
echo "📦 Step 1/5: Creating database 'ai_planner'..."
gcloud sql databases create ai_planner --instance=ai-planner-db 2>/dev/null || echo "Database already exists"

# Step 2: Create user
echo "👤 Step 2/5: Creating database user 'appuser'..."
DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create appuser \
  --instance=ai-planner-db \
  --password="$DB_PASSWORD" 2>/dev/null || echo "User already exists"

echo "   📝 Generated password: $DB_PASSWORD"
echo "   ⚠️  Save this password! You'll need it later."
echo ""

# Step 3: Get connection name
echo "🔗 Step 3/5: Getting Cloud SQL connection name..."
CONNECTION_NAME=$(gcloud sql instances describe ai-planner-db --format="value(connectionName)")
echo "   Connection: $CONNECTION_NAME"
echo ""

# Step 4: Create DATABASE_URL
DATABASE_URL="postgresql://appuser:${DB_PASSWORD}@/ai_planner?host=/cloudsql/${CONNECTION_NAME}"
echo "📝 Step 4/5: Database URL created"
echo ""

# Step 5: Update Cloud Run
echo "🚀 Step 5/5: Updating Cloud Run service..."
gcloud run services update ai-activity-planner \
  --region us-central1 \
  --add-cloudsql-instances "$CONNECTION_NAME" \
  --update-env-vars "DATABASE_URL=$DATABASE_URL"

echo ""
echo "✅ ✅ ✅ SETUP COMPLETE! ✅ ✅ ✅"
echo ""
echo "🎉 Your app now has persistent storage!"
echo ""
echo "📋 Summary:"
echo "   - Database: ai_planner"
echo "   - User: appuser"
echo "   - Password: $DB_PASSWORD"
echo "   - Connection: $CONNECTION_NAME"
echo ""
echo "🌐 Your app is live at:"
echo "   https://ai-activity-planner-300000255718.us-central1.run.app"
echo ""
echo "🔐 IMPORTANT: Save these credentials somewhere safe!"
echo ""
echo "Next steps:"
echo "1. Test your app - user data will now persist!"
echo "2. Save the database password in a secure location"
echo "3. Consider setting up automated backups"
echo ""

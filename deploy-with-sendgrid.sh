#!/bin/bash

# SendGrid Configuration Script
# Replace these values with your actual credentials

SENDGRID_API_KEY="YOUR_API_KEY_HERE"  # From Step 2
EMAIL_FROM="your-email@gmail.com"      # From Step 3 (verified email)

echo "🚀 Deploying with SendGrid configuration..."

gcloud run deploy ai-activity-planner \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "SENDGRID_API_KEY=${SENDGRID_API_KEY},EMAIL_FROM=${EMAIL_FROM}"

echo "✅ Deployment complete!"
echo "📧 Emails will now be sent via SendGrid"

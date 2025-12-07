#!/bin/bash
# Monitor Cloud SQL instance creation

echo "⏳ Monitoring Cloud SQL instance creation..."
echo "This typically takes 5-10 minutes for the first time."
echo ""

while true; do
    STATUS=$(gcloud sql instances describe ai-planner-db --format="value(state)" 2>/dev/null)
    TIMESTAMP=$(date +"%H:%M:%S")
    
    echo "[$TIMESTAMP] Status: $STATUS"
    
    if [ "$STATUS" = "RUNNABLE" ]; then
        echo ""
        echo "✅ ✅ ✅ Cloud SQL instance is READY! ✅ ✅ ✅"
        echo ""
        echo "Now run the setup script:"
        echo "  ./setup_cloudsql.sh"
        break
    fi
    
    sleep 15
done

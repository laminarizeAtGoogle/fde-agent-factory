#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# ==========================================
# PART 1: SETUP & CONFIGURATION
# ==========================================

# 1. Detect Script Location & Project Root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../../.."
ENV_FILE="$PROJECT_ROOT/.env"

# 2. Load .env Configuration
if [ -f "$ENV_FILE" ]; then
  echo "✅ Loading configuration from: .env"
  set -a
  source "$ENV_FILE"
  set +a
else
  echo "⚠️  No .env file found at project root. Using script defaults."
fi

# 3. Set Defaults
: "${SERVICE_NAME:=antigravity-app}"
: "${REGION:=us-central1}"

# ==========================================
# PART 2: PERMISSION CHECKER (New!)
# ==========================================

check_permissions() {
    echo "🔍 Checking Service Account Permissions..."
    
    # Get Project details
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    PROJECT_NUMBER=$(gcloud projects list --filter="projectId:$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null)
    
    # Construct the Default Compute Service Account Email
    COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    
    echo "   Target Account: $COMPUTE_SA"

    # Fetch current roles for this account
    EXISTING_ROLES=$(gcloud projects get-iam-policy $PROJECT_ID \
        --flatten="bindings[].members" \
        --filter="bindings.members=serviceAccount:$COMPUTE_SA" \
        --format="value(bindings.role)")

    MISSING_PERMS=0

    # Check 1: Storage Admin (Fixes "Error 403: storage.objects.get")
    if echo "$EXISTING_ROLES" | grep -q "roles/storage.admin"; then
        echo "   [OK] Storage Admin"
    else
        echo "   [❌] Missing Role: roles/storage.admin"
        MISSING_PERMS=1
    fi

    # Check 2: Artifact Registry Admin (Fixes "Permission denied on resource")
    if echo "$EXISTING_ROLES" | grep -q "roles/artifactregistry.admin"; then
        echo "   [OK] Artifact Registry Admin"
    else
        echo "   [❌] Missing Role: roles/artifactregistry.admin"
        MISSING_PERMS=1
    fi

    # If permissions are missing, generate the fix command
    if [ $MISSING_PERMS -eq 1 ]; then
        echo ""
        echo "🛑 PERMISSION ERROR DETECTED"
        echo "The default Service Account is missing required roles to build from source."
        echo "Please run this command in your terminal to fix it:"
        echo ""
        echo "---------------------------------------------------"
        echo "gcloud projects add-iam-policy-binding $PROJECT_ID --member=\"serviceAccount:$COMPUTE_SA\" --role=\"roles/storage.admin\" && gcloud projects add-iam-policy-binding $PROJECT_ID --member=\"serviceAccount:$COMPUTE_SA\" --role=\"roles/artifactregistry.admin\""
        echo "---------------------------------------------------"
        echo ""
        read -p "Would you like to try deploying anyway? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✅ Permissions look good."
    fi
}

# Run the check
check_permissions

# ==========================================
# PART 3: DEPLOYMENT
# ==========================================

echo "🚀 Starting Cloud Run Source Deploy"
echo "   Service: $SERVICE_NAME"
echo "   Region:  $REGION"

ARGS="--source $PROJECT_ROOT --region $REGION --allow-unauthenticated --quiet"

if [ -f "$ENV_FILE" ]; then
  ARGS="$ARGS --env-vars-file $ENV_FILE"
fi

gcloud run deploy $SERVICE_NAME $ARGS

if [ $? -eq 0 ]; then
  echo "✅ Deployment Complete: $SERVICE_NAME"
else
  echo "❌ Deployment Failed. Review the logs above."
  exit 1
fi
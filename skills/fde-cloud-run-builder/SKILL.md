---
name: fde-cloud-run-builder
description: capable of deploying the current workspace code to Google Cloud Run using Google Cloud Buildpacks (source deploy).
---

# Identity
You are a DevOps engineer responsible for shipping code to production.

# Capabilities
You can deploy the application in the current directory to Google Cloud Run. You do not need a Dockerfile; you utilize the Cloud Run "source deploy" feature to build the container automatically.

# Instructions
1. **Trigger:** When the user asks to "deploy," "ship," "push to cloud," or "update the site," initiate the deployment process.

2. **Configuration Check (Crucial):**
   - Check the **Project Root** for a file named `.env`.
   - **If `.env` is MISSING:** Stop and ask the user: *"I noticed you don't have a `.env` file for configuration. Would you like me to create one for you, or should I proceed with the default settings?"*
   - **If `.env` EXISTS:** Proceed immediately to execution.

3. **Pre-Flight Check:**
   - Ensure `.agents/skills/fde-cloud-run-builder/deploy.sh` exists and is executable.

4. **Execution:**
   - Execute the shell command: `bash .agents/skills/fde-cloud-run-builder/deploy.sh`
   - Note: The script handles the loading of the `.env` file automatically.

5. **Monitoring:**
   - Watch the standard output. If the deployment fails (non-zero exit code), summarize the error for the user.
   - If successful, provide the user with the Service URL returned by the script.

6. **Self-Diagnosis:** The deploy script automatically checks IAM permissions. If it detects missing roles (Storage Admin or Artifact Registry Admin), it will output the specific `gcloud` fix command.
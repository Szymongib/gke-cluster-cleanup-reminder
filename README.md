# GKE Cluster Cleanup Reminder

Quick and dirty Slack bot that reminds you to remove your GKE clusters.

[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

## Overview

If you frequently use GKE clusters for development purposes you may catch yourself that sometimes you forget to delete them after you finished working. This may generate unnecesary costs for you or your company.

This tool can help you by listing all running clusters directly to the Slack channel.

![demo1](./assets/gke_cluster_cleanup_reminder.jpg "Slack message example")


## Usage

Mention your bot user with `@` in the desired channel.


## Run Application

To run application set following environtment variables:
- `GOOGLE_APPLICATION_CREDENTIALS` - path to GCP Service Account (not required while running on Cloud Run)
- `GCP_PROJECT_NAME`
- `SLACK_BOT_USER_ACCESS_TOKEN`
- `SLACK_SIGNING_SECRET`

Install dependencies:
```
pip install -r requirements.txt
```

Run:
```
python3 app/cleanup-reminder.py
```


## Create Slack Application

To create Slack application in your workspace refere to the [documentation](https://api.slack.com/start/overview#creating).


## Configure bot Bot

To configure bot for your Slack channel follow the steps below:
1. Create Slack Application.
2. Navigate to `OAuth & Permissions`
    - Add Bot Token Scopes `app_mentions:read` and `chat:write`
    - Install Application to the Workspace to get `Bot User OAuth Access Token`
3. Use `Run on Google Cloud` button to start deploying the Application
    - Chose the project and region
    - Set environment variables when asked
        - `GCP_PROJECT_NAME` - the project from which the clusters will me checked
        - `SLACK_BOT_USER_ACCESS_TOKEN` - generated after installing Slack App to the workspace
        - `SLACK_SIGNING_SECRET` - can be found in `Basic Information` section of your Slack Application
    > **NOTE:** You may encounter error like `Error: the service did not become ready in 30s`, do not worry if the service stood up later
4. Get the service URL in the Cloud Shell by running:
    ```
    gcloud run services describe gke-cluster-cleanup-reminder --platform managed --region {REGION_YOU_HAVE_CHOSEN} --project {PROJECT_YOU_HAVE_CHOSEN}
    ```
5. Navigate to `Event Subscriptions` and enable it
    - Set the Request URL to the URL of your service (the challange request might need to be retried a few times while the Application spins up)
    - Subscribe to `app_mention` bot event and save the changes
5. Navigate to `Interactivity & Shortcuts` in your Slack Application
    - Set request URL to `{SERVICE_URL}/interactive` and save changes
6. Now you can add bot user to the channel by mentioning it with `@`
    > **NOTE:** You can adjust the bot name and display name in the `App Home`
7. (optional) Set reminder on the channel to mention the bot every day on specific time. For example:
    ```
    /remind @channel "Remove your clusters! @{BOT_USER}" every weekday at 3:30pm
    ```

# Playground 2.0

## Setup
### Pre-reqs
Install dependencies for target app
```
cd target_app
npm install
npm install @ctrlb/heimdall
```
### Install requirements
```
pip install -r requirements.txt
```

### Create config
Create the .env which should look something like
```
DB_USERNAME=...
DB_PASSWORD=...
DB_CLUSTER=...
DB_NAME=...

START_PORT=...
END_PORT=...
KILL_CHILD_PROCESS_IN_SECONDS=...
SLEEP_WATCHER_FOR_SECONDS=...

ENV=PROD
TARGET_APP_BASE_ADDRESS="https://playground.ctrlb.ai/app"
```

### Setup nginx
If you're setting this up in prod, use the `nginx.conf` present here.

## Run
```
python master.py
```
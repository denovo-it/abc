#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Check if required variables are set
if [ -z "$VOYAGER_USER" ] || [ -z "$VOYAGER_TOKEN" ]; then
  echo "Error: VOYAGER_USER and VOYAGER_TOKEN must be set in .env file"
  exit 1
fi

./install.sh --YES --media --user "$VOYAGER_USER" --token "$VOYAGER_TOKEN"

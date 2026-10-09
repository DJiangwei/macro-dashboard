#!/bin/bash
echo "Waiting for build-v4 processes to finish..."
while pgrep -f "make build-v4" > /dev/null; do
    sleep 5
done
echo "Running make validate..."
if make validate; then
    echo "Running make publish..."
    make publish MSG="P5 Generator Consolidation (Fixed all pipelines)"
else
    echo "make validate failed!"
fi

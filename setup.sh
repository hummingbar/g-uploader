#!/bin/sh

echo "Editing USER"

cd /g-uploader

sed -i 's/admin/'"$USER"'/' config.json

echo "Editing Password"

sed -i 's/passwd/'"$PASSWORD"'/' config.json

forever start server.js

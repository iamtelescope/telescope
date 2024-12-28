#!/bin/bash
cd ui
npm run build
cd ..
ls
rm -rf backend/telescope/static
cp -rv ui/dist/static backend/telescope/
cp -rv ui/dist/favicon.ico backend/telescope/static/
cp -rv ui/src/assets/namedlogo.png backend/telescope/static/
cp -rv ui/dist/index.html backend/telescope/templates/
cd backend
cd ..

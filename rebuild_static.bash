#!/bin/bash
cd ui
npm run build
cd ..
ls
rm -rf backend/telescope/static
rm -rf backend/static
cp -rv ui/dist/static backend/telescope/
cp -rv ui/dist/favicon.ico backend/telescope/static/
cp -rv ui/dist/editor.worker.js backend/telescope/static/
cp -rv ui/dist/editor.worker.js.map backend/telescope/static/
cp -rv ui/dist/json.worker.js backend/telescope/static/
cp -rv ui/dist/json.worker.js.map backend/telescope/static/
cp -rv ui/src/assets/namedlogo.png backend/telescope/static/
cp -rv ui/dist/index.html backend/telescope/templates/
cd backend
python manage.py collectstatic
cd ..

# Gestion de parc automobile
parc_automobile/
backend/    Django : API JSON (véhicules, chauffeurs, affectations, entretiens, pannes et réparations)
frontend/   React + Vite : interface web

## Lancer le backend
    cd backend
    python -m venv .env
    .env\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    py manage.py migrate
    py manage.py createsuperuser   /il crée VOTRE compte administrateur
    py manage.py runserver
    http://127.0.0.1:8000

## Lancer le frontend (second terminal)
    cd frontend
    npm install
    npm run dev       
    http://localhost:5173


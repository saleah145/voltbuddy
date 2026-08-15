VoltBuddy missing core services restore

Copy these files into:
~/Desktop/voltbuddy/backend/services/

Files:
- __init__.py
- rates.py
- grid.py
- optimization.py
- recommendations.py

Do NOT delete or replace your newer service files such as:
- appliance_search.py
- appliance_estimates.py
- appliance_catalog.py
or any other catalog/photo-related services.

Then run:
cd ~/Desktop/voltbuddy/backend
python3 -m uvicorn main:app

If it starts, test:
curl --max-time 5 -I http://127.0.0.1:8000/docs

PATA HAO VIEWINGS REFACTOR
==========================

Replace:
backend/viewings/models.py
backend/viewings/serializers.py
backend/viewings/views.py
backend/viewings/urls.py

Then run from the backend folder:

python manage.py makemigrations viewings
python manage.py migrate
python manage.py check

New endpoint:
GET /api/viewings/<id>/timeline/

IMPORTANT NEXT UPDATE
---------------------
Existing partner action endpoints must stop assigning operational values such as
partner_en_route, partner_arrived, or viewing_in_progress to Viewing.status.

Instead, create events using viewing.record_event(...).

Partner confirmation should update Viewing.status to confirmed and create a
partner_confirmed event. Completion should update Viewing.status to completed
and create a viewing_completed event.

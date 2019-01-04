import json

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import forms, tasks


@csrf_exempt
@require_POST
def index(request):
    """
    Accepts data sample, runs basic message-level validation and queues
    for further processing and storage.
    """
    try:
        payload = json.loads(request.body.decode())
    except json.JSONDecodeError:
        return HttpResponseBadRequest()
    form = forms.SeriesForm(data=payload)
    if form.is_valid():
        data = form.cleaned_data
        task = tasks.add_samples.delay(
            samples=[
                [
                    sample['parameter'],
                    sample['instance'],
                    sample['value']
                ]
                for sample in data['samples']
            ],
            host=data['host'],
            mode=False,
            timestamp=data['timestamp']
        )
        response = HttpResponse(status=202)
        response['Location'] = reverse('collector:job',
                                       kwargs={'uuid': task.id})
        return response
    return HttpResponseBadRequest()


@require_GET
def job(request, uuid):
    """
    Looks a job up by UUID and returns it's status data.
    """
    result = tasks.add_samples.AsyncResult(str(uuid))
    return JsonResponse(
        data={
            'uuid': uuid,
            'state': result.state
        },
        json_dumps_params={
            'sort_keys': True
        }
    )

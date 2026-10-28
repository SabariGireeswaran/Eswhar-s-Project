from django.shortcuts import render , redirect
from django.http import HttpResponse , HttpResponseRedirect , JsonResponse , FileResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from models.classifiers import (predict_liverD, predict_heartD, predict_alzheimer,
predict_diabetes, predict_disease)
try:
    from models.transcribe import get_text
except Exception:
    get_text = None
import os
import re
import cv2
import json
import base64
import random
import time
import uuid
import boto3
import numpy as np
from PIL import Image

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}


def _parse_feature_form(post_dict):
    """Pull the numeric model features out of a submitted prediction form,
    excluding the csrf token (previously done positionally via [1:], which
    silently breaks if the token isn't first in the dict)."""
    post_dict = dict(post_dict)
    post_dict.pop('csrfmiddlewaretoken', None)
    return post_dict

# Create your views here
def front(request):
    return render(request , 'front/index.html')

def bmiCalc(request):
    return render(request , 'bmi/bmi-calculator.html')

def heart(request):
    return render(request , 'heart/index.html')

def heartPred(request):
    if request.method == 'POST':
        feature_values = _parse_feature_form(request.POST.dict()).values()
        try:
            features = list(map(float, feature_values))
        except ValueError:
            return HttpResponse("Invalid input: all fields must be numeric.", status=400)
        try:
            pred = predict_heartD(np.array([features]))
        except Exception as e:
            return HttpResponse(f"Could not generate a prediction: {e}", status=400)
        context = {
            'pred':pred
        }
        return render(request , 'heart/output.html' , context)

    else:
        return redirect('heart-disease-view')

def diabetes(request):
    return render(request , 'diabetes/index.html')

def diabetesPred(request):
    if request.method == 'POST':
        feature_values = _parse_feature_form(request.POST.dict()).values()
        try:
            features = list(map(float, feature_values))
        except ValueError:
            return HttpResponse("Invalid input: all fields must be numeric.", status=400)
        try:
            pred = predict_diabetes(np.array([features]))
        except Exception as e:
            return HttpResponse(f"Could not generate a prediction: {e}", status=400)
        context = {
            'pred':pred
        }
        return render(request , 'diabetes/output.html' , context)

    else:
        return redirect('diabetes-view')

def liver(request):
    return render(request , 'liver/index.html')

def liverPred(request):
    if request.method == 'POST':
        out_features = _parse_feature_form(request.POST.dict())
        try:
            features = list(map(float, out_features.values()))
        except ValueError:
            return HttpResponse("Invalid input: all fields must be numeric.", status=400)
        try:
            pred = predict_liverD(np.array([features]))
        except Exception as e:
            return HttpResponse(f"Could not generate a prediction: {e}", status=400)
        context = {
            'pred':pred,
            'out_features':out_features
        }
        return render(request , 'liver/page2.html' , context)

    else:
        return redirect('liver-view')



def alzheimerPred(request):
    if request.method == 'POST':
        img_file = request.FILES.get('image')
        if not img_file:
            return HttpResponse("Please choose an image to upload.", status=400)

        ext = os.path.splitext(img_file.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return HttpResponse(
                "Unsupported file type. Please upload a JPG, PNG or BMP image.", status=400)

        # Save under a generated name instead of the client-supplied one, so
        # an upload can't overwrite another file or inject path characters.
        safe_name = f"{uuid.uuid4().hex}{ext}"
        fss = FileSystemStorage()
        saved_name = fss.save(safe_name, img_file)
        file_path = os.path.join(settings.MEDIA_ROOT, saved_name)

        try:
            img = Image.open(file_path).convert("RGB").resize((224, 224))
        except Exception:
            return HttpResponse("The uploaded file is not a valid image.", status=400)

        cam_path = file_path.replace(ext, "") + "_camViz.jpg"
        try:
            label , cam_path = predict_alzheimer(img , file_path , cam_path)
        except FileNotFoundError as e:
            return HttpResponse(str(e), status=503)
        except Exception as e:
            return HttpResponse(f"Could not generate a prediction: {e}", status=500)

        with open(cam_path, "rb") as img2str:
            converted_string = base64.b64encode(img2str.read())

        context = {
            'file_url': cam_path,
            'label': label,
            'photo': str(converted_string)
        }
        return JsonResponse(context)

    else:
        return render(request , 'alzheimer/Alzheimer.html')



def symptomsDis(request):

    if request.method == 'POST' and 'audio' not in request.FILES:
        values = list(_parse_feature_form(request.POST.dict()).values())
        if not values:
            return JsonResponse({"error": "Please select at least one symptom."}, status=400)
        user_symptoms = values[:-1]
        try:
            days = int(values[-1])
        except ValueError:
            return JsonResponse({"error": "Invalid number of days."}, status=400)
        try:
            advice, output = predict_disease(user_symptoms , days)
        except KeyError as e:
            return JsonResponse({"error": f"Unrecognized symptom: {e}"}, status=400)
        context = {
            "advice":advice,
            "output":output
        }
        return JsonResponse(context)

    if request.method == 'POST' and 'audio' in request.FILES:
        audio_data = request.FILES["audio"]
        # Save under a generated name instead of the client-supplied one, so
        # an upload can't overwrite another file or inject path characters.
        safe_name = f"{uuid.uuid4().hex}.webm"
        fss = FileSystemStorage()
        saved_name = fss.save(safe_name, audio_data)
        file_path = os.path.join(settings.MEDIA_ROOT, saved_name)

        if get_text is None:
            return JsonResponse({
                "error": "Voice transcription is disabled because AWS is not configured."
            })

        text = get_text(file_path, saved_name)
        out = re.findall("[a-zA-Z]+", text)
        try:
            advice, output = predict_disease(out)
        except KeyError as e:
            return JsonResponse({"error": f"Could not recognize symptom from audio: {e}"}, status=400)
        context = {
            "advice":advice,
            "output":output
        }
        return JsonResponse(context)

    else:
        return render(request , 'soundRecorder/recorder.html')
